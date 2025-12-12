
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
    ProviderPlanView,
    purchase_plan,
    purchase_plan
)
router = DefaultRouter()
router.register(r'billing-cycles', BillingCycleViewSet)
router.register(r'plans', PlanViewSet)
router.register(r'coupons', CouponViewSet)
router.register(r'plan-prices', PlanPriceViewSet)
router.register(r'plan-items', PlanItemViewSet)
router.register(r'purchased-plans', PurchasedPlanViewSet)
router.register(r'provider-permissions', ProviderPlanPermissionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('purchase/', purchase_plan, name='purchase-plan'),
    path("provider/plans/", ProviderPlanView.as_view(), name="provider-plans"),

]