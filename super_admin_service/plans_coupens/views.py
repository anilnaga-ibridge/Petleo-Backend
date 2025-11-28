
# from rest_framework import viewsets, status, permissions
# from rest_framework.decorators import action
# from rest_framework.response import Response
# from django.shortcuts import get_object_or_404
# from django.utils import timezone

# from admin_core.authentication import CentralAuthJWTAuthentication as AuthServiceJWTAuthentication

# from admin_core.permissions import IsSuperAdmin
# from .models import BillingCycle, Plan, Coupon, PlanPrice, PlanItem
# # from .serializers import BillingCycleSerializer, PlanSerializer, CouponSerializer

# from .serializers import (
#     BillingCycleSerializer,
#     PlanSerializer,
#     PlanPriceSerializer,
#     PlanItemSerializer,
#     CouponSerializer,
# )
# # -------------------- BILLING CYCLE --------------------
# class BillingCycleViewSet(viewsets.ModelViewSet):
#     """
#     Billing Cycle Management
#     - Super Admin: Full CRUD
#     - Service Provider: Read-only (active ones)
#     """
#     queryset = BillingCycle.objects.all().order_by("id")
#     serializer_class = BillingCycleSerializer
#     authentication_classes = [AuthServiceJWTAuthentication]
#     permission_classes = [permissions.IsAuthenticated]

#     def get_permissions(self):
#         """Only superadmins can modify, others can read."""
#         if self.action in ["create", "update", "partial_update", "destroy"]:
#             return [IsSuperAdmin()]
#         return [permissions.IsAuthenticated()]

#     def get_queryset(self):
#         """Show only active cycles for non-admin users."""
#         queryset = super().get_queryset()
#         user = self.request.user
#         if not getattr(user, "is_staff", False):
#             queryset = queryset.filter(is_active=True)
#         return queryset

#     def destroy(self, request, *args, **kwargs):
#         """Prevent deletion if linked to plans."""
#         instance = self.get_object()
#         linked_plans = instance.plan_set.all()
        
#         print(f"🗑️  Attempting to delete Billing Cycle: {instance.name} (ID: {instance.id})")
        
#         if linked_plans.exists():
#             plans_count = linked_plans.count()
#             print(f"❌ Cannot delete: Billing Cycle is linked to {plans_count} existing plans")
#             return Response(
#                 {
#                     "detail": f"Cannot delete: BillingCycle '{instance.name}' is linked to {plans_count} existing Plans.",
#                     "linked_plans_count": plans_count
#                 },
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         billing_cycle_name = instance.name
#         instance.delete()
#         print(f"✅ Billing Cycle '{billing_cycle_name}' deleted successfully!")
        
#         return Response({
#             "message": f"Billing Cycle '{billing_cycle_name}' deleted successfully"
#         }, status=status.HTTP_200_OK)


# # -------------------- PLAN --------------------
# class PlanViewSet(viewsets.ModelViewSet):
#     """
#     Plan Management
#     - Super Admin: Full CRUD + Publish/Unpublish
#     - Service Provider: Read-only (active plans only)
#     """
#     queryset = Plan.objects.prefetch_related("prices", "items", "items__service", "items__category").all()
#     serializer_class = PlanSerializer
#     authentication_classes = [AuthServiceJWTAuthentication]
#     permission_classes = [permissions.IsAuthenticated]

#     def get_permissions(self):
#         """Super Admin for modification; everyone can read."""
#         if self.action in ["create", "update", "partial_update", "destroy", "publish", "unpublish"]:
#             return [IsSuperAdmin()]
#         return [permissions.IsAuthenticated()]

#     def get_queryset(self):
#         """Active plans only for non-admin users."""
#         queryset = super().get_queryset()
#         user = self.request.user
#         if not getattr(user, "is_staff", False):
#             queryset = queryset.filter(is_active=True)
#         return queryset

#     def list(self, request, *args, **kwargs):
#         """List plans with active filter for service providers."""
#         serializer = self.get_serializer(self.get_queryset(), many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)

#     def destroy(self, request, *args, **kwargs):
#         """Handle plan deletion with cascade delete for related objects."""
#         instance = self.get_object()
        
#         # Get related objects count before deletion for logging
#         prices_count = instance.prices.count()
#         items_count = instance.items.count()
        
#         # Log deletion details
#         print(f"🗑️  Deleting Plan: {instance.title} (ID: {instance.id})")
#         print(f"   Default Billing Cycle: {instance.default_billing_cycle.name if instance.default_billing_cycle else 'None'}")
#         print(f"   Active: {instance.is_active}")
#         print("   Related objects to be deleted:")
#         print(f"   - Prices: {prices_count}")
#         print(f"   - Items: {items_count}")
        
#         # Store plan title for success message
#         plan_title = instance.title
        
#         # Delete the plan (Django will handle cascade deletion)
#         instance.delete()
        
#         print(f"✅ Plan '{plan_title}' deleted successfully!")
        
#         # Return success response with deletion details
#         return Response({
#             "message": f"Plan '{plan_title}' deleted successfully",
#             "deleted_objects": {
#                 "plan": 1,
#                 "prices": prices_count,
#                 "items": items_count
#             }
#         }, status=status.HTTP_200_OK)

#     @action(detail=True, methods=["post"])
#     def publish(self, request, pk=None):
#         """Publish (activate) a plan."""
#         plan = self.get_object()
#         if plan.is_active:
#             return Response({"message": "Plan already active"}, status=status.HTTP_200_OK)

#         plan.is_active = True
#         plan.save(update_fields=["is_active", "updated_at"])
#         return Response({"status": "published"}, status=status.HTTP_200_OK)

#     @action(detail=True, methods=["post"])
#     def unpublish(self, request, pk=None):
#         """Unpublish (deactivate) a plan."""
#         plan = self.get_object()
#         if not plan.is_active:
#             return Response({"message": "Plan already inactive"}, status=status.HTTP_200_OK)

#         plan.is_active = False
#         plan.save(update_fields=["is_active", "updated_at"])
#         return Response({"status": "unpublished"}, status=status.HTTP_200_OK)


# # -------------------- COUPON --------------------
# class CouponViewSet(viewsets.ModelViewSet):
#     """
#     Coupon Management
#     - Super Admin: Full CRUD
#     - Service Provider: Read-only + validation
#     """
#     queryset = Coupon.objects.all().order_by("-created_at")
#     serializer_class = CouponSerializer
#     authentication_classes = [AuthServiceJWTAuthentication]
#     permission_classes = [permissions.IsAuthenticated]

#     def get_permissions(self):
#         """Super Admins can modify; others can only view/validate."""
#         if self.action in ["create", "update", "partial_update", "destroy"]:
#             return [IsSuperAdmin()]
#         return [permissions.IsAuthenticated()]

#     def destroy(self, request, *args, **kwargs):
#         """Handle coupon deletion."""
#         instance = self.get_object()
        
#         print(f"🗑️  Deleting Coupon: {instance.code} (ID: {instance.id})")
#         print(f"   Discount: {instance.discount_value}% ({instance.discount_type})")
#         print(f"   Max Uses: {instance.max_uses}")
#         print(f"   Current Uses: {instance.current_uses}")
        
#         coupon_code = instance.code
#         instance.delete()
#         print(f"✅ Coupon '{coupon_code}' deleted successfully!")
        
#         return Response({
#             "message": f"Coupon '{coupon_code}' deleted successfully"
#         }, status=status.HTTP_200_OK)

#     @action(detail=False, methods=["get"], url_path="validate")
#     def validate_coupon(self, request):
#         """
#         Validate a coupon with params:
#         ?code=COUPON123&plan_id=<uuid>&role=business
#         """
#         code = request.query_params.get("code")
#         plan_id = request.query_params.get("plan_id")
#         role = request.query_params.get("role")

#         if not code:
#             return Response({"detail": "Coupon code is required."}, status=status.HTTP_400_BAD_REQUEST)

#         coupon = get_object_or_404(Coupon, code=code)

#         # Check if valid by date and usage
#         if not coupon.is_valid(now=timezone.now()):
#             return Response(
#                 {"valid": False, "message": "Coupon invalid, expired, or used up."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         # Plan applicability
#         if plan_id and coupon.applies_to_plans.exists():
#             if not coupon.applies_to_plans.filter(pk=plan_id).exists():
#                 return Response(
#                     {"valid": False, "message": "Coupon not applicable to this plan."},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )

#         # Role applicability
#         if role and coupon.applicable_roles and role not in coupon.applicable_roles:
#             return Response(
#                 {"valid": False, "message": "Coupon not applicable to this role."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         return Response({
#             "valid": True,
#             "coupon_code": coupon.code,
#             "discount_type": coupon.discount_type,
#             "discount_value": str(coupon.discount_value),
#             "message": "Coupon is valid."
#         }, status=status.HTTP_200_OK)



from rest_framework import viewsets, status, permissions
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
)
from django.db.models import Q
from .services import assign_plan_permissions_to_user
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

        # Create purchase record
        purchased = PurchasedPlan.objects.create(
            user=user,
            plan=plan,
            billing_cycle=billing_cycle
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
