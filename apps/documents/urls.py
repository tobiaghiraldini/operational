from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'folders', views.DocumentFolderViewSet)
router.register(r'files', views.DocumentFileViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]

