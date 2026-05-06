from django.db import models
from django.core.validators import FileExtensionValidator
from apps.core.models import BaseModel


class DocumentFolder(BaseModel):
    """
    Model representing a folder containing documents to be processed.
    """
    name = models.CharField(max_length=255, help_text="Folder name")
    path = models.CharField(max_length=500, unique=True, help_text="Full path to folder")
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
    file_path = models.CharField(max_length=500, help_text="Full path to file")
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