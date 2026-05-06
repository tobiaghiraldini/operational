from rest_framework import serializers
from .models import DocumentFolder, DocumentFile


class DocumentFolderSerializer(serializers.ModelSerializer):
    file_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentFolder
        fields = '__all__'
    
    def get_file_count(self, obj):
        return obj.files.count()


class DocumentFileSerializer(serializers.ModelSerializer):
    folder_name = serializers.CharField(source='folder.name', read_only=True)
    
    class Meta:
        model = DocumentFile
        fields = '__all__'

