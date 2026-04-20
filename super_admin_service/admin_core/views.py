
# admin_core/viewsets.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import AdminProfile, VerifiedUser, Permission, SuperAdmin, GlobalBranding
from .serializers import (
    AdminProfileSerializer, AdminProfileUpdateSerializer,
    VerifiedUserSerializer, PermissionSerializer, SuperAdminSerializer,
    GlobalBrandingSerializer
)
from .permissions import IsSuperAdmin 

from plans_coupens.models import PurchasedPlan, Plan
from django.db.models import Sum, Count
from datetime import timedelta
from django.utils import timezone
from .analytics_service import (
    get_snapshot, compute_executive_metrics, 
    compute_intelligence_suite, compute_revenue_trend,
    get_operational_alerts
)

class VerifiedUserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only list/retrieve of VerifiedUser (source of truth from Auth Service).
    Other services may need to inspect verified users.
    """
    queryset = VerifiedUser.objects.all()
    serializer_class = VerifiedUserSerializer
    lookup_field = "auth_user_id"


class AdminProfileViewSet(viewsets.ModelViewSet):
    """
    CRUD for AdminProfile.
    External clients should use verified_user auth_user_id as the identifier.
    """
    queryset = AdminProfile.objects.all()
    serializer_class = AdminProfileSerializer
    permission_classes = [IsSuperAdmin]  # adjust as needed
    lookup_field = "verified_user"  # will map to AdminProfile.verified_user (auth_user_id)

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return AdminProfileUpdateSerializer
        return AdminProfileSerializer

    def create(self, request, *args, **kwargs):
        """
        Creating AdminProfile primary flow will happen via Kafka.
        But keep create endpoint to allow manual creation if needed.
        Body expects: verified_user (auth_user_id) and profile fields.
        """
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # soft delete
        instance = self.get_object()
        instance.is_deleted = True
        instance.activity_status = "inactive"
        instance.save(update_fields=["is_deleted", "activity_status", "updated_at"])
        return Response({"message": "Admin soft deleted"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='toggle-status')
    def toggle_status(self, request, verified_user=None):
        admin = self.get_object()
        admin.activity_status = "inactive" if admin.activity_status == "active" else "active"
        admin.save(update_fields=["activity_status", "updated_at"])
        return Response({"message": f"Admin set to {admin.activity_status}"}, status=status.HTTP_200_OK)

    # --- permissions management ---
    @action(detail=True, methods=['post'], url_path='permissions/add')
    def add_permissions(self, request, verified_user=None):
        admin = self.get_object()
        perm_ids = request.data.get("permissions", [])
        perms = Permission.objects.filter(id__in=perm_ids)
        admin.permissions.add(*perms)
        return Response({"message": "Permissions added"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['put'], url_path='permissions/replace')
    def replace_permissions(self, request, verified_user=None):
        admin = self.get_object()
        perm_ids = request.data.get("permissions", [])
        perms = Permission.objects.filter(id__in=perm_ids)
        admin.permissions.set(perms)
        return Response({"message": "Permissions replaced"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='permissions/remove')
    def remove_permissions(self, request, verified_user=None):
        admin = self.get_object()
        perm_ids = request.data.get("permissions", [])
        perms = Permission.objects.filter(id__in=perm_ids)
        admin.permissions.remove(*perms)
        return Response({"message": "Permissions removed"}, status=status.HTTP_200_OK)


class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsSuperAdmin]  # only superadmins manage permission catalogue

class SuperAdminViewSet(viewsets.ModelViewSet):
    queryset = SuperAdmin.objects.all()
    serializer_class = SuperAdminSerializer
    permission_classes = [IsSuperAdmin]
    lookup_field = "id"

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        auth_user_id = request.user.user_id  # from JWT
        superadmin = SuperAdmin.objects.filter(auth_user_id=auth_user_id).first()
        if not superadmin:
            return Response({"detail": "SuperAdmin not found"}, status=404)

        serializer = self.get_serializer(superadmin)
        return Response(serializer.data)




class SuperAdminDashboardViewSet(viewsets.ViewSet):
    """
    Luxury Command Center API - Snapshot Powered.
    """
    permission_classes = [IsSuperAdmin]



    @action(detail=False, methods=['get'])
    def executive_summary(self, request):
        """High-trust KPI Suite with Smart Insights."""
        snapshot = get_snapshot('executive_summary')
        if not snapshot:
            data = compute_executive_metrics()
        else:
            data = snapshot.data_json
        
        return Response({
            "metrics": data,
            "generated_at": snapshot.generated_at if snapshot else timezone.now(),
            "is_stale": snapshot.is_stale if snapshot else True
        })

    @action(detail=False, methods=['get'])
    def revenue(self, request):
        """Dynamic revenue velocity snapshots."""
        snapshot = get_snapshot('revenue_trend')
        if not snapshot:
            from .analytics_service import compute_revenue_trend
            data = compute_revenue_trend()
        else:
            data = snapshot.data_json
        return Response(data)

    @action(detail=False, methods=['get'])
    def intelligence(self, request):
        """Tiered rankings and growth tracking."""
        snapshot = get_snapshot('intelligence_suite')
        if not snapshot:
            data = compute_intelligence_suite()
        else:
            data = snapshot.data_json
        return Response(data)

    @action(detail=False, methods=['get'])
    def risk_center(self, request):
        """Detailed risk alerting."""
        return Response({
            "alerts": get_operational_alerts(),
            "thresholds": {"sync_delay_ms": 1800000} # 30 mins
        })

    @action(detail=False, methods=['get'])
    def health(self, request):
        """Platform vitals."""
        snapshot = get_snapshot('executive_summary')
        health_score = snapshot.data_json.get('platform_health', 100) if snapshot else 100
        return Response({"score": health_score, "status": "OPTIMAL" if health_score >= 90 else "DEGRADED"})


    @action(detail=False, methods=['get'])
    def refresh(self, request):
        """Full rebuild of luxury snapshots."""
        compute_executive_metrics()
        compute_intelligence_suite()
        compute_revenue_trend()
        return Response({"status": "Intelligence suites rebuilding"})




    @action(detail=False, methods=['get'], url_path='plan-buyers/(?P<plan_id>[^/.]+)')
    def plan_buyers(self, request, plan_id=None):
        """Detailed list of buyers for a specific plan with high-trust fallbacks."""
        print(f"🔍 [DEBUG] Hardened fetch for plan_id: {plan_id}")
        plan = get_object_or_404(Plan, id=plan_id)
        purchases = PurchasedPlan.objects.filter(plan=plan).select_related('user')
        
        # Identity Reconciliation (Consistent auth_user_id matching)
        user_auth_ids = [p.user.auth_user_id for p in purchases if p.user.auth_user_id]
        v_users = {v.auth_user_id: v for v in VerifiedUser.objects.filter(auth_user_id__in=user_auth_ids)}
        
        data = []
        for p in purchases:
            v_user = v_users.get(p.user.auth_user_id)
            
            # Layered Metadata Fallback
            full_name = v_user.full_name if v_user and v_user.full_name else (
                f"{p.user.first_name} {p.user.last_name}".strip() or p.user.email.split('@')[0]
            )
            
            # Role Reasoning (Consistent Individual vs Organization labels)
            # Use Plan.target_type as high-trust fallback when identity sync is pending
            raw_role = v_user.role if v_user and v_user.role else p.plan.target_type
            role = raw_role.lower() if raw_role else "organization"
            
            data.append({
                "user_id": str(p.user_id),
                "name": full_name,
                "email": v_user.email if v_user else p.user.email,
                "role": role,
                "status": p.status,
                "purchased_at": p.start_date
            })
            
        print(f"   -> Returning {len(data)} subscribers for {plan.title}")
        return Response({
            "plan_title": plan.title,
            "buyers": data
        })


class GlobalBrandingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing global branding settings.
    """
    queryset = GlobalBranding.objects.all()
    serializer_class = GlobalBrandingSerializer

    def get_permissions(self):
        if self.action == 'public':
            return []
        return [IsSuperAdmin()]

    @action(detail=False, methods=['get'], url_path='public')
    def public(self, request):
        """
        Public endpoint to get the current branding settings.
        """
        branding = GlobalBranding.objects.first()
        if not branding:
            # Return default values if no branding record exists
            return Response({
                "app_name": "PetLeo",
                "primary_color": "#7367F0",
                "secondary_color": "#CE9FFC",
                "logo": None,
                "favicon": None,
                "hide_app_name": False
            })
        serializer = self.get_serializer(branding)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        # Restricted to Super Admin
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        # Allow only one branding record (singleton-ish)
        if GlobalBranding.objects.exists():
            return Response(
                {"detail": "Branding settings already exist. Use update instead."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['patch', 'put'], url_path='update-settings')
    def update_settings(self, request):
        """
        Action to create or update the single global branding record.
        """
        branding = GlobalBranding.objects.first()
        if branding:
            serializer = self.get_serializer(branding, data=request.data, partial=True)
        else:
            serializer = self.get_serializer(data=request.data)
        
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
