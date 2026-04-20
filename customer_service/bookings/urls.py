from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingViewSet, BookingItemViewSet, AnalyticsProViewSet, InvoiceViewSet

router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'items', BookingItemViewSet, basename='booking-item')
router.register(r'analytics-pro', AnalyticsProViewSet, basename='analytics-pro')
router.register(r'invoices', InvoiceViewSet, basename='invoice')

urlpatterns = [
    path('', include(router.urls)),
]
