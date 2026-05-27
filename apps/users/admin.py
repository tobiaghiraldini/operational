from django import forms
from django.contrib import admin, messages
from django.contrib.auth.models import Permission
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.forms import Media
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from unfold.admin import ModelAdmin
from unfold.decorators import action
from tenant_users.permissions.models import UserTenantPermissions
from tenant_users.tenants.models import DeleteError

from apps.core.admin_mixins import PublicSchemaOnlyAdminMixin
from apps.tenants.models import Tenant
from apps.users.models import TenantUser
from apps.users.services import ensure_tenant_membership
from apps.users.services.tenant_permissions_admin import (
    apply_default_business_permissions,
    clear_model_permissions,
    clear_profile_permission_cache,
    get_tenant_permissions_row,
    permissions_queryset_for_tenant,
    set_tenant_user_permissions,
)

PUBLIC_UTP_WARNING = (
    "This row lives in the public schema only. Editing user permissions here does "
    "not grant access to tenant apps (projects, money, etc.). Use "
    "Users → change user → Manage tenant permissions instead."
)


class TenantUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)
    managed_tenants = forms.ModelMultipleChoiceField(
        label="Tenant memberships",
        queryset=Tenant.objects.exclude(schema_name="public").order_by("name"),
        required=False,
        help_text=(
            "Customer tenants only. Membership also creates per-tenant permissions "
            "(required for login/admin in that tenant)."
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
        self.fields["managed_tenants"].queryset = Tenant.objects.exclude(
            schema_name="public"
        ).order_by("name")
        if self.instance and self.instance.pk:
            self.fields["managed_tenants"].initial = self.instance.tenants.exclude(
                schema_name="public"
            )
        self.fields["managed_tenants"].help_text = (
            "Customer tenants only. Every user also belongs to the public tenant "
            "(not listed here) for platform login."
        )


class TenantPermissionsSelectForm(forms.Form):
    tenant = forms.ModelChoiceField(
        label="Tenant",
        queryset=Tenant.objects.exclude(schema_name="public").order_by("name"),
        required=True,
    )


class TenantPermissionsEditForm(forms.Form):
    permissions = forms.ModelMultipleChoiceField(
        label="Permissions",
        queryset=Permission.objects.none(),
        required=False,
        help_text="Chosen permissions are granted to this user in the selected tenant.",
        widget=admin.widgets.FilteredSelectMultiple("Permissions", is_stacked=False),
    )

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant is None:
            return
        self.fields["permissions"].queryset = permissions_queryset_for_tenant(tenant=tenant)
        row = get_tenant_permissions_row(user=user, tenant=tenant)
        if row is None or user is None:
            return
        from django_tenants.utils import tenant_context

        with tenant_context(tenant):
            self.fields["permissions"].initial = list(
                row.user_permissions.values_list("pk", flat=True)
            )


@admin.register(TenantUser)
class TenantUserAdmin(PublicSchemaOnlyAdminMixin, ModelAdmin):
    add_form = TenantUserCreationForm
    form = TenantUserChangeForm
    model = TenantUser
    actions_detail = ("manage_tenant_permissions",)

    list_display = (
        "email",
        "display_name",
        "is_active",
        "is_verified",
        "tenant_permissions_list_link",
    )
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
            {
                "description": (
                    "Membership controls which tenant schemas the user can access. "
                    "Model permissions (projects, money, …) are set separately."
                ),
                "fields": (
                    "public_tenant_membership_note",
                    "managed_tenants",
                    "tenant_is_staff",
                    "tenant_is_superuser",
                    "tenant_permissions_manage_link",
                ),
            },
        ),
        ("Audit", {"fields": ("last_login", "password_changed_at", "invited_by")}),
    )
    add_fieldsets = (
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
                ),
            },
        ),
    )
    readonly_fields = (
        "password_info",
        "last_login",
        "password_changed_at",
        "public_tenant_membership_note",
        "tenant_permissions_manage_link",
    )
    filter_horizontal = ()

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return self.fieldsets

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            for name in (
                "public_tenant_membership_note",
                "tenant_permissions_manage_link",
            ):
                if name not in readonly:
                    readonly.append(name)
        return readonly

    def get_form(self, request, obj=None, change=False, **kwargs):
        """Use TenantUserCreationForm on add (password + tenant membership fields)."""
        defaults = {}
        if obj is None:
            defaults["form"] = self.add_form
        defaults.update(kwargs)
        return super().get_form(request, obj, change=change, **defaults)

    def get_deleted_objects(self, objs, request):
        """Skip Django's deletion collector (tenant-app tables are not in public schema)."""
        obj_list = list(objs)
        if not obj_list:
            return [], {}, set(), []

        opts = self.model._meta
        formatted = []
        for obj in obj_list:
            url = reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[obj.pk])
            formatted.append(
                format_html(
                    '{}: <a href="{}">{}</a>',
                    capfirst(opts.verbose_name),
                    url,
                    obj,
                )
            )
        formatted.append(
            mark_safe(
                "<strong>Effect:</strong> accounts are deactivated (is_active=False), "
                "tenant memberships are updated, and owned tenants are archived. "
                "User rows remain in the database."
            )
        )
        model_count = {opts.verbose_name_plural: len(obj_list)}
        return formatted, model_count, set(), []

    def delete_model(self, request, obj):
        """Deactivate via django-tenant-users (avoids cross-schema hard-delete collector)."""
        self._deactivate_tenant_user(request, obj)

    def delete_queryset(self, request, queryset):
        deactivated = 0
        for user in queryset:
            try:
                TenantUser.objects.delete_user(user)
                deactivated += 1
            except DeleteError as exc:
                self.message_user(
                    request,
                    f"{user.email}: {exc}",
                    level=messages.ERROR,
                )
        if deactivated:
            self.message_user(
                request,
                (
                    f"Deactivated {deactivated} user(s). Memberships were updated; "
                    "rows remain in the database (is_active=False)."
                ),
                level=messages.SUCCESS,
            )

    def _deactivate_tenant_user(self, request, user):
        try:
            TenantUser.objects.delete_user(user)
        except DeleteError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
            return
        self.message_user(
            request,
            (
                f"Deactivated {user.email}. Memberships were updated; "
                "the row remains in the database (is_active=False)."
            ),
            level=messages.SUCCESS,
        )

    def public_tenant_membership_note(self, obj):
        return mark_safe(
            "This user is always a member of the <strong>public</strong> tenant "
            "(platform authentication). It is not shown in the list below and cannot "
            "be removed."
        )

    public_tenant_membership_note.short_description = "Public tenant"

    def tenant_permissions_manage_link(self, obj):
        if not obj or not obj.pk:
            return "-"
        url = reverse(
            "admin:users_tenantuser_manage_tenant_permissions",
            args=[obj.pk],
        )
        return format_html(
            '<a class="text-primary-600 hover:underline font-medium" href="{}">'
            "Manage tenant permissions (per schema) →</a>",
            url,
        )

    tenant_permissions_manage_link.short_description = "Business app permissions"

    def tenant_permissions_list_link(self, obj):
        if not obj or not obj.pk:
            return "-"
        url = reverse(
            "admin:users_tenantuser_manage_tenant_permissions",
            args=[obj.pk],
        )
        return format_html(
            '<a class="text-primary-600 hover:underline" href="{}">Permissions</a>',
            url,
        )

    tenant_permissions_list_link.short_description = "Tenant permissions"

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        user = form.instance
        selected_tenants = set(form.cleaned_data.get("managed_tenants", []))
        current_tenants = set(user.tenants.all())

        public_tenant = Tenant.objects.filter(schema_name="public").first()
        if public_tenant:
            selected_tenants.add(public_tenant)

        is_staff = bool(form.cleaned_data.get("tenant_is_staff", True))
        is_superuser = bool(form.cleaned_data.get("tenant_is_superuser", False))

        for tenant in selected_tenants:
            ensure_tenant_membership(
                user=user,
                tenant=tenant,
                is_staff=is_staff,
                is_superuser=is_superuser,
            )

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
            except Exception as exc:  # pragma: no cover
                self.message_user(
                    request,
                    f"Could not remove {user.email} from {tenant.schema_name}: {exc}",
                    level=messages.ERROR,
                )

        clear_profile_permission_cache(user)

    def password_info(self, obj):
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
            ),
            path(
                "<path:object_id>/tenant-permissions/",
                self.admin_site.admin_view(self.manage_tenant_permissions),
                name=f"{self.opts.app_label}_{self.opts.model_name}_manage_tenant_permissions",
            ),
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

    @action(
        description="Manage tenant permissions",
        permissions=["change"],
    )
    def manage_tenant_permissions(self, request, object_id):
        user = get_object_or_404(TenantUser, pk=object_id)
        if not self.has_change_permission(request, user):
            raise Http404("Permission denied.")

        tenant = None
        tenant_row = None
        permission_count = 0

        if request.method == "POST":
            action = request.POST.get("action", "show")
            tenant_id = request.POST.get("tenant_id")
            if not tenant_id:
                select_form = TenantPermissionsSelectForm(request.POST, prefix="select")
                if select_form.is_valid():
                    tenant_id = str(select_form.cleaned_data["tenant"].pk)
            if tenant_id:
                tenant = get_object_or_404(Tenant, pk=tenant_id)

            if tenant and not user.tenants.filter(pk=tenant.pk).exists():
                self.message_user(
                    request,
                    f"{user.email} is not a member of {tenant.schema_name}.",
                    level=messages.ERROR,
                )
                return HttpResponseRedirect(request.path)

            if tenant and action == "apply_defaults":
                n = apply_default_business_permissions(user=user, tenant=tenant)
                self.message_user(
                    request,
                    f"Applied default business permissions ({n} in policy) on {tenant.schema_name}.",
                    level=messages.SUCCESS,
                )
                return HttpResponseRedirect(f"{request.path}?tenant_id={tenant.pk}")

            if tenant and action == "clear_permissions":
                clear_model_permissions(user=user, tenant=tenant)
                self.message_user(
                    request,
                    f"Cleared direct permissions on {tenant.schema_name}.",
                    level=messages.WARNING,
                )
                return HttpResponseRedirect(f"{request.path}?tenant_id={tenant.pk}")

            if tenant and action == "save_permissions":
                permissions_form = TenantPermissionsEditForm(
                    request.POST,
                    prefix="perms",
                    tenant=tenant,
                    user=user,
                )
                if permissions_form.is_valid():
                    set_tenant_user_permissions(
                        user=user,
                        tenant=tenant,
                        permission_ids=list(
                            permissions_form.cleaned_data["permissions"].values_list(
                                "pk", flat=True
                            )
                        ),
                    )
                    self.message_user(
                        request,
                        f"Saved permissions for {tenant.schema_name}.",
                        level=messages.SUCCESS,
                    )
                    return HttpResponseRedirect(f"{request.path}?tenant_id={tenant.pk}")

        tenant_id_qs = request.GET.get("tenant_id")
        if tenant_id_qs:
            tenant = Tenant.objects.filter(pk=tenant_id_qs).first()

        select_form = TenantPermissionsSelectForm(
            initial={"tenant": tenant} if tenant else None,
            prefix="select",
        )
        permissions_form = TenantPermissionsEditForm(prefix="perms")

        if tenant is not None:
            tenant_row = get_tenant_permissions_row(user=user, tenant=tenant)
            permissions_form = TenantPermissionsEditForm(
                tenant=tenant,
                user=user,
                prefix="perms",
            )
            if tenant_row is not None:
                from django_tenants.utils import tenant_context

                with tenant_context(tenant):
                    permission_count = tenant_row.user_permissions.count()

        select_filter_media = Media(
            css={"all": ["admin/css/widgets.css"]},
            js=[
                "admin/js/core.js",
                "admin/js/SelectBox.js",
                "admin/js/SelectFilter2.js",
            ],
        )
        context = {
            **self.admin_site.each_context(request),
            "title": f"Tenant permissions: {user.email}",
            "form": select_form,
            "permissions_form": permissions_form,
            "opts": self.model._meta,
            "original": user,
            "tenant": tenant,
            "tenant_row": tenant_row,
            "permission_count": permission_count,
            "media": select_filter_media + self.media + permissions_form.media,
        }
        return TemplateResponse(
            request,
            "admin/users/tenantuser/manage_tenant_permissions.html",
            context,
        )


@admin.register(UserTenantPermissions)
class UserTenantPermissionsAdmin(PublicSchemaOnlyAdminMixin, ModelAdmin):
    """Public-schema permission rows (platform only — not tenant app access)."""

    list_display = (
        "profile",
        "is_staff",
        "is_superuser",
        "modified_at",
        "tenant_business_permissions_link",
    )
    list_filter = ("is_staff", "is_superuser")
    search_fields = ("profile__email",)
    raw_id_fields = ("profile",)
    readonly_fields = (
        "public_schema_permissions_warning",
        "tenant_business_permissions_link",
        "created_at",
        "modified_at",
        "groups",
        "user_permissions",
    )
    fields = (
        "public_schema_permissions_warning",
        "tenant_business_permissions_link",
        "profile",
        "is_staff",
        "is_superuser",
        "groups",
        "user_permissions",
        "created_at",
        "modified_at",
    )

    def public_schema_permissions_warning(self, obj=None):
        return format_html("<p><strong>{}</strong></p>", PUBLIC_UTP_WARNING)

    public_schema_permissions_warning.short_description = "Important"

    def tenant_business_permissions_link(self, obj=None):
        if obj is None or not obj.profile_id:
            return "-"
        perms_url = reverse(
            "admin:users_tenantuser_manage_tenant_permissions",
            args=[obj.profile_id],
        )
        user_url = reverse("admin:users_tenantuser_change", args=[obj.profile_id])
        return format_html(
            '<p><a class="text-primary-600 hover:underline font-medium" href="{}">'
            "Manage tenant permissions (projects, money, …)</a></p>"
            '<p class="text-sm opacity-80">User record: '
            '<a class="text-primary-600 hover:underline" href="{}">{}</a></p>',
            perms_url,
            user_url,
            obj.profile.email,
        )

    tenant_business_permissions_link.short_description = "Where to grant access"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.profile_id:
            clear_profile_permission_cache(obj.profile)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if form.instance.profile_id:
            clear_profile_permission_cache(form.instance.profile)
