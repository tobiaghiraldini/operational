from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import DocumentFolder, DocumentFile
from .serializers import DocumentFolderSerializer, DocumentFileSerializer
from apps.core.tenant import TenantSafeQuerysetMixin


class DocumentFolderViewSet(TenantSafeQuerysetMixin, viewsets.ModelViewSet):
    queryset = DocumentFolder.objects.all()
    serializer_class = DocumentFolderSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'auto_process']
    search_fields = ['name', 'path', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class DocumentFileViewSet(TenantSafeQuerysetMixin, viewsets.ModelViewSet):
    queryset = DocumentFile.objects.all()
    serializer_class = DocumentFileSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'file_type', 'folder']
    search_fields = ['filename', 'file_path']
    ordering_fields = ['upload_date', 'processed_at', 'file_size']
    ordering = ['-upload_date']