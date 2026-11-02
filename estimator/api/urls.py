"""API routes (spec section 13)."""
from django.urls import path

from . import views

urlpatterns = [
    path('estimate/', views.EstimateView.as_view(), name='estimate'),
    path('immigration/', views.ImmigrationView.as_view(), name='immigration'),
]
