# from django.urls import path, include
# from rest_framework.routers import DefaultRouter
# from .views import BillingCycleViewSet, PlanViewSet, CouponViewSet

# # Initialize router
# router = DefaultRouter()

# # Register all viewsets
# router.register(r'billing-cycles', BillingCycleViewSet, basename='billing-cycle')
# router.register(r'plans', PlanViewSet, basename='plan')
# router.register(r'coupons', CouponViewSet, basename='coupon')

# # Include router URLs
# urlpatterns = [
#     path('', include(router.urls)),
# ]
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BillingCycleViewSet,
    PlanViewSet,
    PlanPriceViewSet,
    PlanItemViewSet,
    CouponViewSet,
    PurchasedPlanViewSet,
    ProviderPlanPermissionViewSet,
    purchase_plan,
)
router = DefaultRouter()
router.register("billing-cycles", BillingCycleViewSet)
router.register("plans", PlanViewSet)
router.register("plan-prices", PlanPriceViewSet)
router.register("plan-items", PlanItemViewSet)
router.register("coupons", CouponViewSet)
router.register(r"purchased-plans", PurchasedPlanViewSet, basename="purchased-plans")
router.register(r"provider-permissions", ProviderPlanPermissionViewSet, basename="provider-permissions")

urlpatterns = [
    path("", include(router.urls)),
     path("purchase-plan/", purchase_plan, name="purchase-plan"),
]