from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.knowledge.models import (
    Article,
    EntityLink,
    KnowledgeRelation,
    KnowledgeSource,
)


class EntityLinkInline(TabularInline):
    model = EntityLink
    extra = 0


@admin.register(Article)
class ArticleAdmin(ModelAdmin):
    list_display = ("title", "article_kind", "updated_at")
    list_filter = ("article_kind",)
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "body")
    filter_horizontal = ("topics",)
    inlines = [EntityLinkInline]


@admin.register(KnowledgeSource)
class KnowledgeSourceAdmin(ModelAdmin):
    list_display = ("source_type", "reference", "status", "processed_at")
    list_filter = ("source_type", "status")


@admin.register(KnowledgeRelation)
class KnowledgeRelationAdmin(ModelAdmin):
    list_display = ("relation_type", "source_content_type", "source_object_id", "target_content_type", "target_object_id")
    list_filter = ("relation_type",)
