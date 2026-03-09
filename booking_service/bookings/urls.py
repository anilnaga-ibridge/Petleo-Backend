from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BookingViewSet, BookingItemViewSet, VisitGroupViewSet,
    SubscriptionPlanViewSet, ProviderSubscriptionViewSet
)

router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'items', BookingItemViewSet, basename='booking-item')
router.register(r'visit', VisitGroupViewSet, basename='visit')
router.register(r'subscription-plans', SubscriptionPlanViewSet, basename='subscription-plan')
router.register(r'subscriptions', ProviderSubscriptionViewSet, basename='subscription')

urlpatterns = [
    path('', include(router.urls)),
]
