# provider_home/views.py
from django.utils import timezone
from django.db import models
from django.core.cache import cache

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from admin_core.permissions import IsSuperAdmin

from .models import ProviderHomePage
from .serializers import ProviderHomePageSerializer

# Import your Plan model + serializer (adjust path if different)
from plans_coupens.models import Plan
from plans_coupens.serializers import PlanSerializer

CACHE_TTL = 60  # seconds (tweak in settings later)

class ProviderHomePageViewSet(viewsets.ModelViewSet):
    """
    SuperAdmin CRUD for full page content (inlines managed via admin or separate endpoints).
    Restricted to IsSuperAdmin.
    """
    queryset = ProviderHomePage.objects.all().order_by("-publish_at", "-updated_at")
    serializer_class = ProviderHomePageSerializer
    permission_classes = [IsSuperAdmin]

    def perform_create(self, serializer):
        # Optionally set created_by from request user (if available)
        user = getattr(self.request, "user", None)
        serializer.save(created_by=user)

    def perform_update(self, serializer):
        user = getattr(self.request, "user", None)
        # bump version on update
        instance = serializer.save(updated_by=user, version=(serializer.instance.version or 1) + 1)
        return instance


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def provider_home(request):
    """
    Public provider home endpoint used by providers frontends.
    Returns the latest published ProviderHomePage for the user's provider_type
    plus filtered plans.
    Caches result per provider_type for CACHE_TTL seconds.
    """
    provider_type = getattr(request.user, "provider_type", None)
    if provider_type not in ["individual", "organization"]:
        return Response({"detail": "Not a provider user"}, status=status.HTTP_403_FORBIDDEN)

    cache_key = f"provider_home:{provider_type}"
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    # Query published pages matching provider_type or both, respecting publish_at
    page_qs = ProviderHomePage.objects.filter(
        provider_type__in=["both", provider_type],
        is_published=True
    ).filter(
        models.Q(publish_at__isnull=True) | models.Q(publish_at__lte=timezone.now())
    ).order_by("-publish_at", "-updated_at")

    page = page_qs.prefetch_related(
        "hero_banners", "banner_slides", "images", "features",
        "testimonials", "videos", "services", "faqs"
    ).first()

    page_serialized = ProviderHomePageSerializer(page).data if page else None

    plans = Plan.objects.filter(role=provider_type, is_active=True).order_by("created_at")
    plans_serialized = PlanSerializer(plans, many=True).data

    payload = {
        "provider_type": provider_type,
        "page": page_serialized,
        "plans": plans_serialized
    }

    cache.set(cache_key, payload, CACHE_TTL)
    return Response(payload, status=status.HTTP_200_OK)
@api_view(["GET"])
@permission_classes([IsSuperAdmin])
def page_preview_url(request, pk):
    """
    Returns a frontend preview URL for the homepage.
    Used by IFRAME preview inside the admin builder.
    """
    from django.conf import settings

    page = ProviderHomePage.objects.filter(id=pk).first()
    if not page:
        return Response({"detail": "Page not found"}, status=404)

    FRONTEND = getattr(settings, "FRONTEND_ORIGIN", "http://localhost:5173")
    
    # This route must exist in frontend (PublicPreviewRenderer.vue)
    preview_url = f"{FRONTEND}/preview/home/{pk}"

    return Response({"preview_url": preview_url})
