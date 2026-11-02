"""URL configuration: the API lives under /api/ (estimator/api/urls.py)."""
from django.urls import include, path

urlpatterns = [
    path('api/', include('estimator.api.urls')),
]
