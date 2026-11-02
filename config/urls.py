"""URL configuration: the front end at /, the API under /api/ (estimator/api/urls.py)."""
from django.urls import include, path

from estimator.views import index

urlpatterns = [
    path('', index, name='index'),
    path('api/', include('estimator.api.urls')),
]
