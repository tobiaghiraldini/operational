from django.db import models


class SubscriptionTier(models.Model):
    """Subscription tier (shared): defines which features are available."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    # Feature flags or limits can be added (JSONField or separate model) later.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscriptions_tier"
        verbose_name = "Subscription tier"
        verbose_name_plural = "Subscription tiers"

    def __str__(self):
        return self.name
