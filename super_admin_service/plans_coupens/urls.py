
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PlanViewSet,
    PlanCapabilityViewSet,
    CouponViewSet,
    PurchasedPlanViewSet,
    ProviderPlanCapabilityViewSet,
    ProviderPlanView,
    purchase_plan,
    BillingCycleConfigViewSet
)
router = DefaultRouter()
router.register(r'plans', PlanViewSet)
router.register(r'coupons', CouponViewSet)
router.register(r'plan-capabilities', PlanCapabilityViewSet)
router.register(r'purchased-plans', PurchasedPlanViewSet)
router.register(r'provider-capabilities', ProviderPlanCapabilityViewSet)
router.register(r'billing-cycles', BillingCycleConfigViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('purchase/', purchase_plan, name='purchase-plan'),
    path("provider/plans/", ProviderPlanView.as_view(), name="provider-plans"),

]