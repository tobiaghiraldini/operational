from django import forms
from django.contrib import admin, messages
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from tenant_users.constants import TENANT_CACHE_NAME

from apps.core.admin_mixins import PublicSchemaOnlyAdminMixin
from apps.tenants.models import Tenant
from apps.users.models import TenantUser
from apps.users.services import ensure_tenant_membership


class TenantUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)
    managed_tenants = forms.ModelMultipleChoiceField(
        label="Tenant memberships",
        queryset=Tenant.objects.all(),
        required=False,
        help_text=(
            "Assign this user to tenants via a safe flow that creates per-tenant "
            "permissions (required for login/admin in that tenant)."
        ),
    )
    tenant_is_staff = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Grant staff access in selected tenants (recommended for admin login).",
    )
    tenant_is_superuser = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Grant superuser access in selected tenants.",
    )

    class Meta:
        model = TenantUser
        fields = ("email", "display_name", "is_active", "is_verified")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class TenantUserChangeForm(forms.ModelForm):
    managed_tenants = forms.ModelMultipleChoiceField(
        label="Tenant memberships",
        queryset=Tenant.objects.all(),
        required=False,
        help_text=(
            "Use this field instead of the raw M2M relation so tenant permissions "
            "are created/updated correctly."
        ),
    )
    tenant_is_staff = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Applied when adding the user to a tenant.",
    )
    tenant_is_superuser = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Applied when adding the user to a tenant.",
    )

    class Meta:
        model = TenantUser
        fields = (
            "email",
            "display_name",
            "is_active",
            "is_verified",
            "managed_tenants",
            "tenant_is_staff",
            "tenant_is_superuser",
            "timezone",
            "locale",
            "phone",
            "avatar",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["managed_tenants"].initial = self.instance.tenants.all()


@admin.register(TenantUser)
class TenantUserAdmin(PublicSchemaOnlyAdminMixin, ModelAdmin):
    add_form = TenantUserCreationForm
    form = TenantUserChangeForm
    model = TenantUser

    list_display = ("email", "display_name", "is_active", "is_verified")
    ordering = ("email",)
    search_fields = ("email", "display_name")
    list_filter = ("is_active", "is_verified")

    fieldsets = (
        (None, {"fields": ("email", "password_info")}),
        (
            "Profile",
            {"fields": ("display_name", "timezone", "locale", "phone", "avatar")},
        ),
        ("Status", {"fields": ("is_active", "is_verified")}),
        (
            "Tenant access",
            {"fields": ("managed_tenants", "tenant_is_staff", "tenant_is_superuser")},
        ),
        ("Audit", {"fields": ("last_login", "password_changed_at", "invited_by")}),
    )
    add_fieldsets = fieldsets
    readonly_fields = ("password_info", "last_login", "password_changed_at")
    filter_horizontal = ()

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return (
                (
                    None,
                    {
                        "fields": (
                            "email",
                            "password1",
                            "password2",
                            "display_name",
                            "is_active",
                            "is_verified",
                            "managed_tenants",
                            "tenant_is_staff",
                            "tenant_is_superuser",
                        )
                    },
                ),
            )
        return self.fieldsets

    def get_form(self, request, obj=None, **kwargs):
        defaults = {}
        defaults["form"] = self.add_form if obj is None else self.form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

    def save_related(self, request, form, formsets, change):
        """Synchronize tenant memberships via tenant-aware permission rows."""
        super().save_related(request, form, formsets, change)
        user = form.instance
        selected_tenants = set(form.cleaned_data.get("managed_tenants", []))
        current_tenants = set(user.tenants.all())

        # Ensure users always belong to the public tenant.
        public_tenant = Tenant.objects.filter(schema_name="public").first()
        if public_tenant:
            selected_tenants.add(public_tenant)

        is_staff = bool(form.cleaned_data.get("tenant_is_staff", True))
        is_superuser = bool(form.cleaned_data.get("tenant_is_superuser", False))

        # Ensure permissions exist for all selected tenants (including pre-existing links).
        for tenant in selected_tenants:
            ensure_tenant_membership(
                user=user,
                tenant=tenant,
                is_staff=is_staff,
                is_superuser=is_superuser,
            )

        # Remove memberships that are no longer selected.
        to_remove = current_tenants - selected_tenants
        for tenant in to_remove:
            if tenant.schema_name == "public":
                continue
            if tenant.owner_id == user.id:
                self.message_user(
                    request,
                    f"Skipped removal from {tenant.schema_name}: user is tenant owner.",
                    level=messages.WARNING,
                )
                continue
            try:
                tenant.remove_user(user)
            except Exception as exc:  # pragma: no cover - defensive admin flow
                self.message_user(
                    request,
                    f"Could not remove {user.email} from {tenant.schema_name}: {exc}",
                    level=messages.ERROR,
                )

        # Clear cached tenant permission facade values.
        user.__dict__.pop(TENANT_CACHE_NAME, None)

    def password_info(self, obj):
        """Show password hash info + change-password link in change form."""
        if not obj or not obj.pk:
            return "-"
        url = reverse(
            f"admin:{self.opts.app_label}_{self.opts.model_name}_password_change",
            args=[obj.pk],
        )
        return format_html(
            "Raw passwords are not stored. "
            '<a class="text-primary-600 hover:underline" href="{}">Change password</a>',
            url,
        )

    password_info.short_description = "Password"

    def get_urls(self):
        custom = [
            path(
                "<path:object_id>/password/",
                self.admin_site.admin_view(self.user_change_password),
                name=f"{self.opts.app_label}_{self.opts.model_name}_password_change",
            )
        ]
        return custom + super().get_urls()

    def user_change_password(self, request, object_id, form_url=""):
        user = self.get_object(request, object_id)
        if user is None:
            raise Http404("User not found.")
        if not self.has_change_permission(request, user):
            raise Http404("Permission denied.")

        if request.method == "POST":
            form = AdminPasswordChangeForm(user, request.POST)
            if form.is_valid():
                form.save()
                self.message_user(request, "Password changed successfully.", level=messages.SUCCESS)
                return redirect(
                    reverse(
                        f"admin:{self.opts.app_label}_{self.opts.model_name}_change",
                        args=[user.pk],
                    )
                )
        else:
            form = AdminPasswordChangeForm(user)

        context = {
            **self.admin_site.each_context(request),
            "title": f"Change password: {user.email}",
            "form": form,
            "object": user,
            "original": user,
            "opts": self.model._meta,
            "is_popup": False,
            "media": self.media + form.media,
        }
        return TemplateResponse(request, "admin/auth/user/change_password.html", context)
