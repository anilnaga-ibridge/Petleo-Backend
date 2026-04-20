import logging

from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from admin_core.authentication import CentralAuthJWTAuthentication as AuthServiceJWTAuthentication

from admin_core.permissions import IsSuperAdmin
from .models import Plan, Coupon, PlanCapability, PurchasedPlan, ProviderPlanCapability, BillingCycleConfig
from .kafka_producer import publish_permissions_updated, publish_plan_status_changed
from .serializers import (
    PlanSerializer,
    PlanCapabilitySerializer,
    CouponSerializer,
    PurchasedPlanSerializer, ProviderPlanCapabilitySerializer,
    ProviderPlanViewSerializer,
    BillingCycleConfigSerializer,
    InvoiceSerializer,
)
from django.db.models import Q
from .services import assign_plan_permissions_to_user, calculate_end_date
from django.db import transaction

logger = logging.getLogger(__name__)

# -------------------- BILLING CYCLE CONFIG --------------------
class BillingCycleConfigViewSet(viewsets.ModelViewSet):
    queryset = BillingCycleConfig.objects.all().order_by("duration_days")
    serializer_class = BillingCycleConfigSerializer
    permission_classes = [IsSuperAdmin]

# -------------------- PLAN --------------------
class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.all().order_by("-created_at")
    serializer_class = PlanSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        qs = super().get_queryset()

        target_type = self.request.query_params.get("target_type")
        if target_type:
            qs = qs.filter(target_type=target_type)

        return qs

    def perform_update(self, serializer):
        instance = self.get_object()
        old_status = instance.is_active
        updated_instance = serializer.save()
        new_status = updated_instance.is_active

        if old_status != new_status:
            print(f"DEBUG: Plan {updated_instance.id} status changed: {old_status} -> {new_status}")
            publish_plan_status_changed(updated_instance.id, new_status)


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
                        "permissions": cap.permissions,
                        "limits": cap.limits,
                        "facilities": []
                    }
                
                if not cap.facility:
                    # Category-level permissions
                    grouped[s_id]["categories"][c_id]["permissions"] = cap.permissions
                    grouped[s_id]["categories"][c_id]["limits"] = cap.limits
                else:
                    # Facility
                    grouped[s_id]["categories"][c_id]["facilities"].append({
                        "id": str(cap.facility.id),
                        "name": cap.facility.name,
                        "permissions": cap.permissions,
                        "limits": cap.limits
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

        plan_id = self.request.query_params.get("plan")
        if plan_id:
            qs = qs.filter(plan_id=plan_id)

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

    @action(detail=True, methods=["post"], url_path="refresh-entitlements", permission_classes=[IsAuthenticated])
    def refresh_entitlements(self, request, pk=None):
        """
        Manually trigger a cross-service entitlement synchronization.
        POST /api/superadmin/purchased-plans/{pk}/refresh-entitlements/
        """
        plan = self.get_object()
        
        # Security: only owner or superadmin can refresh
        if not request.user.is_superuser and plan.user != request.user:
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
            
        from .billing_service import EntitlementOrchestrator
        success, msg = EntitlementOrchestrator.trigger_sync(plan, reason="MANUAL_REFRESH")
        
        if success:
            return Response({"detail": msg}, status=status.HTTP_200_OK)
        else:
            return Response({"detail": msg}, status=status.HTTP_429_TOO_MANY_REQUESTS if "Rate limit" in msg else status.HTTP_400_BAD_REQUEST)

# -------------------- PROVIDER PLAN PERMISSIONS --------------------
class ProviderPlanCapabilityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProviderPlanCapability.objects.all()
    serializer_class = ProviderPlanCapabilitySerializer
    permission_classes = [IsSuperAdmin]


# Purchase endpoint (any authenticated user can purchase)
from rest_framework.permissions import IsAuthenticated, AllowAny

from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from rest_framework.permissions import IsAuthenticated, AllowAny
from admin_core.authentication import CentralAuthJWTAuthentication as AuthServiceJWTAuthentication
from admin_core.permissions import IsSuperAdmin
from .models import (
    Plan, Coupon, PlanCapability, PurchasedPlan, 
    ProviderPlanCapability, BillingCycleConfig, Invoice
)
from .billing_service import InvoiceOrchestrator, SettlementService
from .pdf_engine import PDFEngine
from admin_core.models import ProviderBillingProfile

# ... (Previous ViewSets preserved)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def purchase_plan(request):
    """
    Initiates the B2B purchase flow.
    Returns an ISSUED invoice.
    """
    user = request.user
    plan_id = request.data.get("plan_id")

    if not plan_id:
        return Response({"detail": "plan_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    plan = get_object_or_404(Plan, id=plan_id)
    if not plan.is_active:
        return Response({"detail": "This plan is no longer available."}, status=status.HTTP_400_BAD_REQUEST)

    # 1. Ensure Billing Profile exists
    billing_profile = getattr(user, 'billing_profile', None)
    if not billing_profile:
        return Response({
            "detail": "Billing profile missing. Please complete organization details first.",
            "code": "BILLING_PROFILE_MISSING"
        }, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        # 2. Create PENDING purchase
        purchased = PurchasedPlan.objects.create(
            user=user,
            plan=plan,
            billing_cycle=plan.billing_cycle,
            status="PENDING",
            is_active=False
        )

        # 3. Use Orchestrator to generate Invoice with Snapshots
        invoice = InvoiceOrchestrator.create_invoice(purchased, user, billing_profile)
        
        # 4. Generate PDF async/immediately for the ISSUED state
        PDFEngine.generate_invoice_pdf(invoice.id)

    return Response({
        "message": "Purchase initiated. Please complete payment.",
        "purchase_id": str(purchased.id),
        "invoice_number": invoice.invoice_number,
        "total_amount": str(invoice.total_amount),
        "currency": invoice.currency,
        "payment_url": f"/billing/pay/{invoice.id}" # Simulated gateway link
    }, status=status.HTTP_201_CREATED)


class PaymentWebhookView(generics.GenericAPIView):
    """
    Secure HMAC-verified endpoint for payment settlements.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        payload = request.body.decode('utf-8')
        # 0. Mock Bypass for Testing (only in DEBUG)
        is_mock = request.headers.get('X-Mock-Payment') == 'true'
        if settings.DEBUG and is_mock:
            logger.info("🛠️ DEBUG: Processing MOCK payment bypass.")
        else:
            if not all([signature, timestamp, nonce]):
                return Response({"detail": "Security headers missing"}, status=status.HTTP_401_UNAUTHORIZED)

            # 1. Signature & Replay Verification
            if not SettlementService.verify_webhook_signature(payload, signature, timestamp, nonce):
                return Response({"detail": "Invalid signature or replay window"}, status=status.HTTP_401_UNAUTHORIZED)

        # 2. Process Settlement (Atomic & Idempotent)
        data = request.data
        invoice_id = data.get("invoice_id")
        payment_ref = data.get("payment_ref")
        
        try:
            success = SettlementService.process_payment_success(invoice_id, payment_ref, data)
            if success:
                return Response({"status": "settled"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Settlement failed: {e}")
            return Response({"detail": "Settlement error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"status": "failed"}, status=status.HTTP_400_BAD_REQUEST)


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provider-facing Invoice ViewSet.
    Allows listing own invoices and downloading PDFs.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        return Invoice.objects.filter(provider=self.request.user)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        invoice = self.get_object()
        if not invoice.pdf_file:
            # Regenerate if missing
            PDFEngine.generate_invoice_pdf(invoice.id)
            invoice.refresh_from_db()
            
        return Response({"download_url": invoice.pdf_file.url})

    @action(detail=False, methods=["get"], url_path="migration-record/(?P<recovery_id>[^/.]+)/download", permission_classes=[IsAuthenticated])
    def download_migration_record(self, request, recovery_id=None):
        """
        Download an audit-safe migration record PDF.
        """
        from .models import LegacyEntitlementRecovery
        import uuid
        
        # Check if recovery_id is a UUID or a record number
        try:
            uuid.UUID(recovery_id)
            lookup = {"id": recovery_id}
        except (ValueError, TypeError, AttributeError):
            lookup = {"migration_record_number": recovery_id}
            
        recovery = get_object_or_404(LegacyEntitlementRecovery, **lookup)
        
        # Security: owner or superadmin
        is_staff = getattr(request.user, 'is_staff', False)
        is_super = getattr(request.user, 'is_super_admin', False)
        
        if not (is_staff or is_super) and recovery.purchased_plan.user != request.user:
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
            
        pdf_path = recovery.metadata_json.get("pdf_record_path")
        if not pdf_path:
             from .pdf_engine import PDFEngine
             pdf_path = PDFEngine.generate_migration_record_pdf(recovery.id)
             
        return Response({"download_url": pdf_path})

    @action(detail=False, methods=["get"], url_path="summary")
    def billing_summary(self):
        """
        Quick stats for Dashboard.
        """
        qs = self.get_queryset()
        return Response({
            "active_plan": PurchasedPlanSerializer(
                PurchasedPlan.objects.filter(user=self.request.user, is_active=True).first()
            ).data,
            "pending_invoices": qs.filter(status="ISSUED").count(),
            "total_spent": sum(i.total_amount for i in qs.filter(status="PAID"))
        })



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
             # Check JSON permissions
             return perm.permissions.get(f"can_{action}", False)
        return False
    except Exception:
        return False


class ProviderPlanView(generics.ListAPIView):
    serializer_class = ProviderPlanViewSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Plan.objects.filter(is_active=True).order_by("created_at")
        
        # Support both target_type and role
        target_type = self.request.query_params.get("target_type")
        role = self.request.query_params.get("role")

        print(f"DEBUG: ProviderPlanView params: {self.request.query_params}")
        print(f"DEBUG: Initial Plan Count: {qs.count()}")

        if role:
            target_type = role.upper()
        
        print(f"DEBUG: Filtering by target_type: {target_type}")

        if target_type:
            qs = qs.filter(target_type__iexact=target_type)
            
        print(f"DEBUG: Final Plan Count: {qs.count()}")
        return qs
