
from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from admin_core.authentication import CentralAuthJWTAuthentication as AuthServiceJWTAuthentication

from admin_core.permissions import IsSuperAdmin
from .models import BillingCycle, Plan, Coupon, PlanPrice, PlanCapability, PurchasedPlan, ProviderPlanCapability
# from .serializers import BillingCycleSerializer, PlanSerializer, CouponSerializer
from .kafka_producer import publish_permissions_updated
from .serializers import (
    BillingCycleSerializer,
    PlanSerializer,
    PlanPriceSerializer,
    PlanCapabilitySerializer,
    CouponSerializer,
    PurchasedPlanSerializer, ProviderPlanCapabilitySerializer,
    ProviderPlanViewSerializer,
)
from django.db.models import Q
from .services import assign_plan_permissions_to_user, calculate_end_date
from django.db import transaction

# -------------------- BILLING CYCLE --------------------
class BillingCycleViewSet(viewsets.ModelViewSet):
    queryset = BillingCycle.objects.all()
    serializer_class = BillingCycleSerializer
    permission_classes = [IsSuperAdmin]
# -------------------- PLAN --------------------
class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.all().order_by("-created_at")
    serializer_class = PlanSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        qs = super().get_queryset()

        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)

        return qs

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def permissions(self, request, pk=None):
        """
        GET /api/superadmin/plans/{pk}/permissions/
        Returns hierarchical list of permissions for this plan.
        """
        plan = self.get_object()
        capabilities = plan.capabilities.select_related('service', 'category', 'facility').all()
        
        # Group by Service -> Category
        grouped = {}
        
        for cap in capabilities:
            if not cap.service: continue
            
            s_id = str(cap.service.id)
            if s_id not in grouped:
                grouped[s_id] = {
                    "service_id": s_id,
                    "service_name": cap.service.display_name,
                    "service_icon": cap.service.icon,
                    "categories": {}
                }
            
            if cap.category:
                c_id = str(cap.category.id)
                if c_id not in grouped[s_id]["categories"]:
                    grouped[s_id]["categories"][c_id] = {
                        "category_id": c_id,
                        "category_name": cap.category.name,
                        "permissions": {
                            "can_view": False, "can_create": False, "can_edit": False, "can_delete": False
                        },
                        "facilities": []
                    }
                
                if not cap.facility:
                    # Category-level permissions
                    grouped[s_id]["categories"][c_id]["permissions"] = {
                        "can_view": cap.can_view,
                        "can_create": cap.can_create,
                        "can_edit": cap.can_edit,
                        "can_delete": cap.can_delete,
                    }
                else:
                    # Facility
                    grouped[s_id]["categories"][c_id]["facilities"].append({
                        "id": str(cap.facility.id),
                        "name": cap.facility.name,
                        "permissions": {
                            "can_view": cap.can_view,
                            "can_create": cap.can_create,
                            "can_edit": cap.can_edit,
                            "can_delete": cap.can_delete,
                        }
                    })

        # Flatten for response
        permissions_list = []
        for s_val in grouped.values():
            cats = list(s_val["categories"].values())
            permissions_list.append({
                "service_id": s_val["service_id"],
                "service_name": s_val["service_name"],
                "service_icon": s_val["service_icon"],
                "categories": cats
            })

        return Response({
            "plan_id": str(plan.id),
            "permissions": permissions_list
        })


# -------------------- PLAN PRICE --------------------
class PlanPriceViewSet(viewsets.ModelViewSet):
    queryset = PlanPrice.objects.all()
    serializer_class = PlanPriceSerializer
    permission_classes = [IsSuperAdmin]
# -------------------- PLAN CAPABILITY --------------------
class PlanCapabilityViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for PlanCapability
    - SuperAdmin only
    """

    serializer_class = PlanCapabilitySerializer
    permission_classes = [IsSuperAdmin]

    # Preload related objects → huge performance improvement
    queryset = (
        PlanCapability.objects
        .select_related("plan", "service", "category", "facility")
        .order_by("-id")
    )

    def get_queryset(self):
        qs = super().get_queryset()

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(plan__title__icontains=search)
                | Q(service__display_name__icontains=search)
                | Q(category__name__icontains=search)
            )

        return qs

    def create(self, request, *args, **kwargs):
        serializer = PlanCapabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        return Response(PlanCapabilitySerializer(item).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = PlanCapabilitySerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()

        return Response(PlanCapabilitySerializer(item).data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        DELETE /plan-capabilities/<uuid>/
        """
        instance = self.get_object()
        instance.delete()
        return Response({"detail": "Plan capability deleted"}, status=status.HTTP_204_NO_CONTENT)
# -------------------- COUPON --------------------
class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.all().order_by("-created_at")
    serializer_class = CouponSerializer
    permission_classes = [IsSuperAdmin]  # or [IsSuperAdmin]
    @action(detail=True, methods=["get"])
    def validate_coupon(self, request, pk=None):
        coupon = self.get_object()
        is_valid = coupon.is_valid()
        return Response({"valid": is_valid}, status=200)
# -------------------- PURCHASED PLAN & PERMISSIONS --------------------

class PurchasedPlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PurchasedPlan.objects.all()
    serializer_class = PurchasedPlanSerializer
    permission_classes = [IsSuperAdmin]

    @action(detail=False, methods=["post"], url_path="check-expiry")
    def check_expiry(self, request):
        """
        Manually trigger a check for expired plans.
        POST /api/superadmin/purchased-plans/check-expiry/
        """
        now = timezone.now()
        expired_plans = PurchasedPlan.objects.filter(is_active=True, end_date__lt=now)
        
        count = 0
        for plan in expired_plans:
            try:
                with transaction.atomic():
                    # 1. Deactivate Plan
                    plan.is_active = False
                    plan.save(update_fields=["is_active"])

                    # 2. Remove Permissions
                    deleted_count, _ = ProviderPlanCapability.objects.filter(
                        user=plan.user, 
                        plan=plan.plan
                    ).delete()

                    # 3. Publish Kafka Event
                    from .kafka_producer import publish_permissions_revoked
                    publish_permissions_revoked(
                        auth_user_id=str(plan.user.id),
                        purchase_id=str(plan.id)
                    )
                    count += 1
            except Exception as e:
                print(f"Error expiring plan {plan.id}: {e}")

        return Response({"message": f"Expired {count} plans."}, status=status.HTTP_200_OK)

# -------------------- PROVIDER PLAN PERMISSIONS --------------------
class ProviderPlanCapabilityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProviderPlanCapability.objects.all()
    serializer_class = ProviderPlanCapabilitySerializer
    permission_classes = [IsSuperAdmin]


# Purchase endpoint (any authenticated user can purchase)
from rest_framework.permissions import IsAuthenticated, AllowAny

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def purchase_plan(request):
    """
    Body:
    {
      "plan_id": "<uuid>",
      "billing_cycle_id": <int>   // optional
    }
    """
    user = request.user
    plan_id = request.data.get("plan_id")
    billing_cycle_id = request.data.get("billing_cycle_id")

    with open("purchase_debug.log", "a") as f:
        f.write(f"Purchase Request: User={user}, Plan={plan_id}\n")

    if not plan_id:
        return Response({"detail": "plan_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    plan = get_object_or_404(Plan, id=plan_id)

    billing_cycle = None
    if billing_cycle_id:
        billing_cycle = get_object_or_404(BillingCycle, id=billing_cycle_id)

    # -------------------------------------------------------------------
    # PURCHASE + ASSIGN PERMISSIONS + PUBLISH KAFKA EVENT
    # -------------------------------------------------------------------
    with transaction.atomic():

        # Calculate End Date
        start_date = timezone.now()
        end_date = None

        if billing_cycle:
            end_date = calculate_end_date(
                start_date, 
                billing_cycle.duration_value, 
                billing_cycle.duration_type
            )

        # Create or Update purchase record
        purchased, created = PurchasedPlan.objects.update_or_create(
            user=user,
            plan=plan,
            billing_cycle=billing_cycle,
            defaults={
                "start_date": start_date,
                "end_date": end_date,
                "is_active": True
            }
        )

        # Assign permissions inside SuperAdmin DB
        assign_plan_permissions_to_user(user, plan)

        # Build permissions payload
        perms = ProviderPlanCapability.objects.filter(user=user, plan=plan)

        permissions_list = [
            {
                "service_id": str(p.service_id) if p.service_id else None,
                "category_id": str(p.category_id) if p.category_id else None,
                "facility_id": str(p.facility_id) if p.facility_id else None,
                "can_view": p.can_view,
                "can_create": p.can_create,
                "can_edit": p.can_edit,
                "can_delete": p.can_delete,
            }
            for p in perms
        ]

        # -------------------------------------------------------------------
        # FETCH TEMPLATES FOR SYNC
        # -------------------------------------------------------------------
        # 1. Get all services allowed in the plan
        allowed_service_ids = set()
        for p in perms:
            if p.service_id:
                allowed_service_ids.add(p.service_id)

        # 2. Fetch full objects
        from dynamic_services.models import Service
        from dynamic_categories.models import Category
        from dynamic_facilities.models import Facility
        from dynamic_pricing.models import Pricing

        services = Service.objects.filter(id__in=allowed_service_ids)
        
        # 3. Construct Payload
        print(f"DEBUG: Constructing templates payload for {len(allowed_service_ids)} services")
        
        templates_payload = {
            "services": [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "display_name": s.display_name,
                    "icon": s.icon
                } for s in services
            ],
            "categories": [], # Will fill below
            "facilities": [], # Will fill below
            "pricing": []     # Will fill below
        }

        # ---------------------------------------------------------
        # REFINED FETCHING FROM PERMISSIONS
        # ---------------------------------------------------------
        seen_categories = set()
        seen_facilities = set()
        allowed_category_ids = set()
        allowed_facility_ids = set()

        # 1. Categories & Facilities from Permissions
        for p in perms:
            # Categories
            if p.category:
                if p.category.id not in seen_categories:
                    templates_payload["categories"].append({
                        "id": str(p.category.id),
                        "service_id": str(p.category.service.id),
                        "name": p.category.name,
                        "is_template": True
                    })
                    seen_categories.add(p.category.id)
                    allowed_category_ids.add(p.category.id)

            # Facilities (if this capability is for a specific facility)
            if p.facility:
                if p.facility.id not in seen_facilities:
                    templates_payload["facilities"].append({
                        "id": str(p.facility.id),
                        "category_id": str(p.category.id) if p.category else None, # Facility might not strictly need category here if global, but usually does
                        "name": p.facility.name,
                        "description": p.facility.description
                    })
                    seen_facilities.add(p.facility.id)
                    allowed_facility_ids.add(p.facility.id)

        # 2. Pricing Rules
        # Filter pricing to only include rules relevant to allowed services, categories, and facilities
        all_pricing = Pricing.objects.filter(service__id__in=allowed_service_ids)
        
        for p in all_pricing:
            # Rule 1: Must match service (already filtered)
            
            # Rule 2: If category is set, it must be in allowed_category_ids
            if p.category and p.category.id not in allowed_category_ids:
                continue
                
            # Rule 3: If facility is set, it must be in allowed_facility_ids
            if p.facility and p.facility.id not in allowed_facility_ids:
                continue
                
            templates_payload["pricing"].append({
                "id": str(p.id),
                "service_id": str(p.service.id),
                "category_id": str(p.category.id) if p.category else None,
                "facility_id": str(p.facility.id) if p.facility else None,
                "price": float(p.price),
                "duration": p.duration,
                "description": "",
                "is_template": True
            })
        
        stats_msg = f"DEBUG: Payload Stats - Services: {len(templates_payload['services'])}, Categories: {len(templates_payload['categories'])}, Facilities: {len(templates_payload['facilities'])}, Pricing: {len(templates_payload['pricing'])}\n"
        print(stats_msg)
        with open("purchase_debug.log", "a") as f:
            f.write(stats_msg)
            f.write(f"Templates: {templates_payload}\n")

        purchased_plan_data = {
            "plan_id": str(plan.id),
            "plan_title": plan.title,
            "billing_cycle_id": billing_cycle.id if billing_cycle else None,
        }

        # Publish Kafka Event
        print("DEBUG: Kafka Producer sending templates...")
        publish_permissions_updated(
            auth_user_id=str(user.auth_user_id),
            purchase_id=str(purchased.id),
            permissions_list=permissions_list,
            purchased_plan=purchased_plan_data,
            templates=templates_payload
        )

    return Response(
        {
            "detail": "Plan purchased and permissions assigned",
            "purchase_id": str(purchased.id)
        },
        status=status.HTTP_201_CREATED
    )


# small helper
def user_has_permission(user, service, category, action: str) -> bool:
    """
    action = "view"|"create"|"edit"|"delete"
    """
    try:
        # This helper might need refinement if we check facility-level permissions
        # For now, checking category level
        perm = ProviderPlanCapability.objects.filter(user=user, service=service, category=category, facility__isnull=True).first()
        if perm:
             return getattr(perm, f"can_{action}", False)
        return False
    except Exception:
        return False


class ProviderPlanView(generics.ListAPIView):
    serializer_class = ProviderPlanViewSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Plan.objects.filter(is_active=True).order_by("created_at")
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        return qs
