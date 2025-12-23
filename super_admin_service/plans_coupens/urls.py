
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BillingCycleViewSet,
    PlanViewSet,
    PlanPriceViewSet,
    PlanCapabilityViewSet,
    CouponViewSet,
    PurchasedPlanViewSet,
    ProviderPlanCapabilityViewSet,
    ProviderPlanView,
    purchase_plan
)
router = DefaultRouter()
router.register(r'billing-cycles', BillingCycleViewSet)
router.register(r'plans', PlanViewSet)
router.register(r'coupons', CouponViewSet)
router.register(r'plan-prices', PlanPriceViewSet)
router.register(r'plan-capabilities', PlanCapabilityViewSet)
router.register(r'purchased-plans', PurchasedPlanViewSet)
router.register(r'provider-capabilities', ProviderPlanCapabilityViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('purchase/', purchase_plan, name='purchase-plan'),
    path("provider/plans/", ProviderPlanView.as_view(), name="provider-plans"),

]