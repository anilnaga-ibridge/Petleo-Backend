from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingViewSet, BookingItemViewSet

router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'items', BookingItemViewSet, basename='booking-item')

urlpatterns = [
    path('', include(router.urls)),
]
