from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PricingRuleViewSet

router = DefaultRouter()
router.register("pricing-rules", PricingRuleViewSet, basename="pricing-rules")

urlpatterns = [
    path("", include(router.urls)),
]
