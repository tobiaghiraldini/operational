from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "invoices"

router = DefaultRouter()
router.register(r'invoices', views.InvoiceViewSet)
router.register(r'extractions', views.InvoiceExtractionViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/process-upload/', views.process_upload, name='process_upload'),
    path('api/upload-batch-zip/', views.upload_invoice_zip_batch, name='upload_invoice_zip_batch'),
    path('api/task-status/<str:task_id>/', views.check_task_status, name='check_task_status'),
    path('api/create-vendor/', views.create_vendor_quick, name='create_vendor_quick'),
    path('api/create-customer/', views.create_customer_quick, name='create_customer_quick'),
    path('', views.invoice_list, name='invoice_list'),
    path('upload/', views.invoice_upload, name='invoice_upload'),
    path('<int:pk>/pdf/', views.invoice_pdf_view, name='invoice_pdf'),
    path('<int:pk>/verify/', views.invoice_verify, name='invoice_verify'),
]

