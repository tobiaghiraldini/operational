from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Article(models.Model):
    """Knowledge article. Tenant-scoped."""

    class ArticleKind(models.TextChoices):
        ARTICLE = "article", "Article"
        PROCEDURE = "procedure", "Procedure"
        CHEATSHEET = "cheatsheet", "Cheatsheet"
        PATTERN = "pattern", "Pattern"
        OTHER = "other", "Other"

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    body = models.TextField(blank=True)
    article_kind = models.CharField(
        max_length=20,
        choices=ArticleKind.choices,
        default=ArticleKind.ARTICLE,
    )
    topics = models.ManyToManyField(
        "topics.Topic",
        blank=True,
        related_name="articles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_article"
        ordering = ["-updated_at"]
        verbose_name = "Article"
        verbose_name_plural = "Articles"

    def __str__(self):
        return self.title


class Book(models.Model):
    """Knowledge book. Tenant-scoped."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_book"
        ordering = ["name"]


class Course(models.Model):
    """Knowledge course. Tenant-scoped."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_course"
        ordering = ["name"]


class KnowledgeSource(models.Model):
    """Source used to populate knowledge (URL, PDF, import)."""

    class SourceType(models.TextChoices):
        URL = "url", "URL"
        PDF = "pdf", "PDF"
        IMPORT = "import", "Import"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
    )
    reference = models.CharField(max_length=500, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    articles = models.ManyToManyField(
        Article,
        blank=True,
        related_name="sources",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_source"
        ordering = ["-created_at"]
        verbose_name = "Knowledge source"
        verbose_name_plural = "Knowledge sources"

    def __str__(self):
        return f"{self.get_source_type_display()}: {self.reference[:50]}"


class KnowledgeRelation(models.Model):
    """Directed relation between domain entities for graph and tree navigation."""

    class RelationType(models.TextChoices):
        MADE_OF = "made_of", "Made of"
        DEPENDS_ON = "depends_on", "Depends on"
        TAGS = "tags", "Tags"
        RELATED = "related", "Related"
        USES = "uses", "Uses"

    source_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="knowledge_relations_out",
    )
    source_object_id = models.PositiveIntegerField()
    source = GenericForeignKey("source_content_type", "source_object_id")
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="knowledge_relations_in",
    )
    target_object_id = models.PositiveIntegerField()
    target = GenericForeignKey("target_content_type", "target_object_id")
    relation_type = models.CharField(
        max_length=20,
        choices=RelationType.choices,
        default=RelationType.RELATED,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "knowledge_relation"
        indexes = [
            models.Index(fields=["source_content_type", "source_object_id"]),
            models.Index(fields=["target_content_type", "target_object_id"]),
        ]
        verbose_name = "Knowledge relation"
        verbose_name_plural = "Knowledge relations"

    def __str__(self):
        return f"{self.relation_type}: {self.source} -> {self.target}"


class EntityLink(models.Model):
    """Links an article to a domain entity."""

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="entity_links",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        db_table = "knowledge_entity_link"
        unique_together = ("article", "content_type", "object_id")
        verbose_name = "Entity link"
        verbose_name_plural = "Entity links"

    def __str__(self):
        return f"{self.article} -> {self.content_object}"
