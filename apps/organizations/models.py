from django.db import models
from django_tenants.utils import get_public_schema_name, schema_context

from apps.core.models import BaseModel


class Organization(BaseModel):
    """
    Optional 1:1 tenant company profile (stored in the tenant schema).

    Holds legal/fiscal identity and branding used for invoice classification
    and extraction context. Replaces the former public-schema TenantCompanyProfile.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    legal_name = models.CharField(max_length=255, blank=True)
    trading_name = models.CharField(max_length=255, blank=True)
    vat_id = models.CharField(max_length=64, blank=True)
    tax_id = models.CharField(max_length=64, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    legal_address = models.TextField(blank=True)
    city = models.CharField(max_length=128, blank=True)
    postal_code = models.CharField(max_length=32, blank=True)
    country_code = models.CharField(max_length=2, default="IT")
    trading_aliases = models.JSONField(default=list, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=64, blank=True)
    website = models.URLField(blank=True)
    logo_url = models.URLField(blank=True)
    tenant = models.OneToOneField(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="organization",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Organization (company profile)"
        verbose_name_plural = "Organizations (company profiles)"

    def __str__(self):
        return self.legal_name or self.trading_name or self.name

    @property
    def display_name(self) -> str:
        return self.trading_name or self.legal_name or self.name

    @property
    def name_for_matching(self) -> str:
        """Alias expected by invoice matching services (same as display_name)."""
        return self.display_name

    @property
    def tax_code(self) -> str:
        """Backward-compatible alias for Italian tax code / codice fiscale."""
        return self.tax_id

    def get_all_names(self) -> list[str]:
        names: list[str] = []
        for value in (self.legal_name, self.trading_name, self.name):
            if value and value not in names:
                names.append(value)
        tenant_name = self._tenant_name_from_public()
        if tenant_name and tenant_name not in names:
            names.append(tenant_name)
        for alias in self.trading_aliases or []:
            if isinstance(alias, str) and alias.strip() and alias.strip() not in names:
                names.append(alias.strip())
        return names

    def _tenant_name_from_public(self) -> str:
        tid = getattr(self, "tenant_id", None)
        if not tid:
            return ""
        from apps.tenants.models import Tenant

        with schema_context(get_public_schema_name()):
            return Tenant.objects.filter(pk=tid).values_list("name", flat=True).first() or ""

    def formatted_address(self) -> str:
        line_parts = [self.address_line1, self.address_line2, self.city, self.postal_code, self.country_code]
        structured = ", ".join(p for p in line_parts if p)
        if structured:
            return structured
        return (self.legal_address or "").strip()
