from rest_framework import serializers
from .models import Invoice, InvoiceExtraction


class InvoiceSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    is_paid = serializers.BooleanField(read_only=True)
    days_overdue = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Invoice
        fields = '__all__'


class InvoiceExtractionSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    
    class Meta:
        model = InvoiceExtraction
        fields = '__all__'

