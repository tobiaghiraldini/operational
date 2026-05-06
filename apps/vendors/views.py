from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Vendor, PaymentMethod
from .serializers import VendorSerializer, PaymentMethodSerializer


class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'country_code']
    search_fields = ['name', 'vat_id', 'email']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class PaymentMethodViewSet(viewsets.ModelViewSet):
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'code']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'code']
    ordering = ['name']