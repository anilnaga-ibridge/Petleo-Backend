

from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import action, api_view, permission_classes
from admin_core.authentication import CentralAuthJWTAuthentication as AuthServiceJWTAuthentication

from admin_core.permissions import IsSuperAdmin
from .models import BillingCycle, Plan, Coupon, PlanPrice, PlanItem,PurchasedPlan, ProviderPlanPermission
# from .serializers import BillingCycleSerializer, PlanSerializer, CouponSerializer
from .kafka_producer import publish_permissions_updated
from .models import ProviderPlanPermission
from .serializers import (
    BillingCycleSerializer,
    PlanSerializer,
    PlanPriceSerializer,
    PlanItemSerializer,
    CouponSerializer,
     PurchasedPlanSerializer, ProviderPlanPermissionSerializer,
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

    @action(detail=True, methods=["get"])
    def permissions(self, request, pk=None):
        """
        GET /api/superadmin/plans/{pk}/permissions/
        Returns list of permissions (PlanItems) for this plan.
        """
        plan = self.get_object()
        items = plan.items.all()
        
        # Transform to simple permission codes or return full items
        # User requested: ["create_service", "view_bookings"]
        # We will map PlanItems to codes.
        
        permissions_list = []
        services_map = {}

        for item in items:
            svc = item.service.name.lower().replace(" ", "_") if item.service else "global"
            cat = item.category.name.lower().replace(" ", "_") if item.category else "all"
            
            if item.can_view: permissions_list.append(f"view_{svc}")
            if item.can_create: permissions_list.append(f"create_{svc}")
            if item.can_edit: permissions_list.append(f"edit_{svc}")
            if item.can_delete: permissions_list.append(f"delete_{svc}")
            
            # Collect Service Details
            if item.service and item.service.id not in services_map:
                services_map[item.service.id] = {
                    "id": str(item.service.id),
                    "name": item.service.display_name,
                    "icon": item.service.icon or "tabler-box", # Default icon
                }
            
        return Response({
            "plan_id": str(plan.id),
            "permissions": permissions_list,
            "services": list(services_map.values())
        })


# -------------------- PLAN PRICE --------------------
class PlanPriceViewSet(viewsets.ModelViewSet):
    queryset = PlanPrice.objects.all()
    serializer_class = PlanPriceSerializer
    permission_classes = [IsSuperAdmin]
# -------------------- PLAN ITEM --------------------
class PlanItemViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for PlanItem
    - SuperAdmin only
    - Prevents duplicate plan+service+category
    - Supports search
    """

    serializer_class = PlanItemSerializer
    permission_classes = [IsSuperAdmin]

    # Preload related objects → huge performance improvement
    queryset = (
        PlanItem.objects
        .select_related("plan", "service", "category")
        .prefetch_related("facilities")
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
        serializer = PlanItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        return Response(PlanItemSerializer(item).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = PlanItemSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()

        return Response(PlanItemSerializer(item).data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        DELETE /plan-items/<uuid>/
        """
        instance = self.get_object()
        instance.delete()
        return Response({"detail": "Plan item deleted"}, status=status.HTTP_204_NO_CONTENT)
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
                    deleted_count, _ = ProviderPlanPermission.objects.filter(
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
class ProviderPlanPermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProviderPlanPermission.objects.all()
    serializer_class = ProviderPlanPermissionSerializer
    permission_classes = [IsSuperAdmin]


# Purchase endpoint (any authenticated user can purchase)
from rest_framework.permissions import IsAuthenticated

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

        # Create purchase record
        purchased = PurchasedPlan.objects.create(
            user=user,
            plan=plan,
            billing_cycle=billing_cycle,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )

        # Assign permissions inside SuperAdmin DB
        assign_plan_permissions_to_user(user, plan)

        # Build permissions payload
        perms = ProviderPlanPermission.objects.filter(user=user, plan=plan)

        permissions_list = [
            {
                "service_id": str(p.service_id) if p.service_id else None,
                "category_id": str(p.category_id) if p.category_id else None,
                "can_view": p.can_view,
                "can_create": p.can_create,
                "can_edit": p.can_edit,
                "can_delete": p.can_delete,
                "facilities": [str(f.id) for f in p.facilities.all()],
            }
            for p in perms
        ]

        purchased_plan_data = {
            "plan_id": str(plan.id),
            "plan_title": plan.title,
            "billing_cycle_id": billing_cycle.id if billing_cycle else None,
        }

        # Publish Kafka Event
        publish_permissions_updated(
            auth_user_id=str(user.id),
            purchase_id=str(purchased.id),
            permissions_list=permissions_list,
            purchased_plan=purchased_plan_data
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
        perm = ProviderPlanPermission.objects.get(user=user, service=service, category=category)
        return getattr(perm, f"can_{action}", False)
    except ProviderPlanPermission.DoesNotExist:
        return False


class ProviderPlanView(generics.ListAPIView):
    serializer_class = ProviderPlanViewSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Plan.objects.filter(is_active=True).order_by("created_at")

