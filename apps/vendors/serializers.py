from rest_framework import serializers
from .models import Vendor, PaymentMethod


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = '__all__'


class VendorSerializer(serializers.ModelSerializer):
    invoice_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Vendor
        fields = '__all__'
    
    def get_invoice_count(self, obj):
        return obj.invoices.count()

