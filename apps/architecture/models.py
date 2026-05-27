from django.db import models


class ArchitectureProfile(models.Model):
    """Software architecture profile for a project (e.g. production, staging)."""

    class Environment(models.TextChoices):
        PROD = "prod", "Production"
        STAGING = "staging", "Staging"
        DEV = "dev", "Development"
        OTHER = "other", "Other"

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="architecture_profiles",
    )
    name = models.CharField(max_length=255)
    environment = models.CharField(
        max_length=20,
        choices=Environment.choices,
        default=Environment.PROD,
    )
    is_primary = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "architecture_profile"
        ordering = ["project", "-is_primary", "name"]
        verbose_name = "Architecture profile"
        verbose_name_plural = "Architecture profiles"

    def __str__(self):
        return f"{self.project.name}: {self.name}"


class ArchitectureComponent(models.Model):
    """Infrastructure or platform component in an architecture profile."""

    class ComponentType(models.TextChoices):
        DATABASE = "database", "Database"
        CACHE = "cache", "Cache"
        SEARCH_ENGINE = "search_engine", "Search engine"
        OBJECT_STORAGE = "object_storage", "Object storage"
        DATA_WAREHOUSE = "data_warehouse", "Data warehouse"
        MESSAGE_BROKER = "message_broker", "Message broker"
        EVENT_BUS = "event_bus", "Event bus"
        TASK_QUEUE = "task_queue", "Task queue"
        LOAD_BALANCER = "load_balancer", "Load balancer"
        REVERSE_PROXY = "reverse_proxy", "Reverse proxy"
        API_GATEWAY = "api_gateway", "API gateway"
        CDN = "cdn", "CDN"
        DNS = "dns", "DNS"
        FIREWALL = "firewall", "Firewall"
        VPN = "vpn", "VPN"
        APPLICATION_SERVER = "application_server", "Application server"
        CONTAINER_RUNTIME = "container_runtime", "Container runtime"
        ORCHESTRATOR = "orchestrator", "Orchestrator"
        SERVERLESS = "serverless", "Serverless"
        VM = "vm", "Virtual machine"
        METRICS = "metrics", "Metrics"
        LOGGING = "logging", "Logging"
        TRACING = "tracing", "Tracing"
        ALERTING = "alerting", "Alerting"
        SECRETS_MANAGER = "secrets_manager", "Secrets manager"
        CERTIFICATE_STORE = "certificate_store", "Certificate store"
        WAF = "waf", "WAF"
        CUSTOM = "custom", "Custom"

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        ACTIVE = "active", "Active"
        DEPRECATED = "deprecated", "Deprecated"

    profile = models.ForeignKey(
        ArchitectureProfile,
        on_delete=models.CASCADE,
        related_name="components",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    component_type = models.CharField(
        max_length=30,
        choices=ComponentType.choices,
        default=ComponentType.CUSTOM,
    )
    vendor = models.CharField(max_length=100, blank=True)
    engine = models.CharField(max_length=100, blank=True)
    system = models.ForeignKey(
        "systems.System",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="architecture_components",
    )
    host = models.CharField(max_length=255, blank=True)
    port = models.PositiveIntegerField(null=True, blank=True)
    region = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "architecture_component"
        ordering = ["profile", "name"]
        unique_together = ("profile", "slug")
        verbose_name = "Architecture component"
        verbose_name_plural = "Architecture components"

    def __str__(self):
        return f"{self.name} ({self.get_component_type_display()})"


class ArchitectureConnection(models.Model):
    """Connection between architecture components."""

    class ConnectionType(models.TextChoices):
        DEPENDS_ON = "depends_on", "Depends on"
        ROUTES_TO = "routes_to", "Routes to"
        REPLICATES_TO = "replicates_to", "Replicates to"
        READS_FROM = "reads_from", "Reads from"
        WRITES_TO = "writes_to", "Writes to"
        PUBLISHES_TO = "publishes_to", "Publishes to"
        SUBSCRIBES_TO = "subscribes_to", "Subscribes to"

    source = models.ForeignKey(
        ArchitectureComponent,
        on_delete=models.CASCADE,
        related_name="outgoing_connections",
    )
    target = models.ForeignKey(
        ArchitectureComponent,
        on_delete=models.CASCADE,
        related_name="incoming_connections",
    )
    connection_type = models.CharField(
        max_length=20,
        choices=ConnectionType.choices,
        default=ConnectionType.DEPENDS_ON,
    )
    label = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "architecture_connection"
        verbose_name = "Architecture connection"
        verbose_name_plural = "Architecture connections"

    def __str__(self):
        return f"{self.source} {self.connection_type} {self.target}"
