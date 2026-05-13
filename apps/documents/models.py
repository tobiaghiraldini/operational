import hashlib
import os

from django.db import models
from django.core.validators import FileExtensionValidator
from apps.core.models import BaseModel
from apps.documents.storage import document_absolute_path, document_upload_to

_DOCUMENT_EXTENSIONS = ("pdf", "png", "jpg", "jpeg", "tif", "tiff", "csv")


class DocumentFolder(BaseModel):
    """
    Model representing a folder containing documents to be processed.
    """
    name = models.CharField(max_length=255, help_text="Folder name")
    path = models.CharField(
        max_length=500,
        unique=True,
        help_text="Path relative to MEDIA_ROOT (e.g. invoices/received). Not an absolute filesystem path.",
    )
    description = models.TextField(blank=True, help_text="Folder description")
    is_active = models.BooleanField(default=True, help_text="Whether folder is being monitored")
    auto_process = models.BooleanField(default=True, help_text="Whether to automatically process new files")
    
    class Meta:
        ordering = ['name']
        verbose_name = "Document Folder"
        verbose_name_plural = "Document Folders"
    
    def __str__(self):
        return self.name


class DocumentFile(BaseModel):
    """
    Model tracking individual document files.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Processing'),
        ('processing', 'Currently Processing'),
        ('processed', 'Successfully Processed'),
        ('error', 'Processing Error'),
        ('skipped', 'Skipped'),
    ]
    
    folder = models.ForeignKey(
        DocumentFolder, 
        on_delete=models.CASCADE, 
        related_name='files',
        help_text="Parent folder"
    )
    
    # File information
    filename = models.CharField(max_length=255, help_text="Original filename")
    file = models.FileField(
        upload_to=document_upload_to,
        blank=True,
        null=True,
        max_length=512,
        validators=[FileExtensionValidator(allowed_extensions=list(_DOCUMENT_EXTENSIONS))],
        help_text="Stored file under MEDIA (preferred).",
    )
    file_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Legacy absolute or MEDIA-relative path; prefer ``file`` for new rows.",
    )
    file_size = models.IntegerField(help_text="File size in bytes")
    file_hash = models.CharField(max_length=64, blank=True, help_text="File hash for duplicate detection")
    
    # Processing status
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        help_text="Processing status"
    )
    processed_at = models.DateTimeField(null=True, blank=True, help_text="When processing completed")
    error_message = models.TextField(blank=True, help_text="Error message if processing failed")
    
    # Metadata
    file_type = models.CharField(max_length=10, default='pdf', help_text="File type/extension")
    upload_date = models.DateTimeField(auto_now_add=True, help_text="When file was first detected")
    
    class Meta:
        unique_together = ['folder', 'filename']
        ordering = ['-upload_date']
        verbose_name = "Document File"
        verbose_name_plural = "Document Files"
    
    def __str__(self):
        return f"{self.filename} ({self.status})"

    def recompute_file_metadata(self) -> None:
        """Set ``file_size`` and ``file_hash`` from the resolved on-disk file."""
        path = document_absolute_path(self)
        if not path or not os.path.isfile(path):
            return
        self.file_size = os.path.getsize(path)
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(4096), b""):
                digest.update(chunk)
        self.file_hash = digest.hexdigest()