from django.db import models


class Article(models.Model):
    """Knowledge article. Tenant-scoped. Links to topics and other entities via relations (later)."""

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_article"
        ordering = ["-updated_at"]
        verbose_name = "Article"
        verbose_name_plural = "Articles"

    def __str__(self):
        return self.title


class Topic(models.Model):
    """Topic: main concept that tags knowledge, products, parts, systems. Tenant-scoped."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_topic"
        ordering = ["name"]


class Book(models.Model):
    """Book: knowledge book. Tenant-scoped."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_book"
        ordering = ["name"]


class Course(models.Model):
    """Course: knowledge course. Tenant-scoped."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_course"
        ordering = ["name"]