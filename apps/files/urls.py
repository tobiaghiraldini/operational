from django.urls import include, path

urlpatterns = [
    path("filepond/", include("django_drf_filepond.urls")),
]
