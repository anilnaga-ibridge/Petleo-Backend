from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BillingCycleViewSet, PlanViewSet, CouponViewSet

# Initialize router
router = DefaultRouter()

# Register all viewsets
router.register(r'billing-cycles', BillingCycleViewSet, basename='billing-cycle')
router.register(r'plans', PlanViewSet, basename='plan')
router.register(r'coupons', CouponViewSet, basename='coupon')

# Include router URLs
urlpatterns = [
    path('', include(router.urls)),
]
