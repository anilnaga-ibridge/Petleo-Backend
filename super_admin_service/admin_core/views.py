
# admin_core/viewsets.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import AdminProfile, VerifiedUser, Permission, SuperAdmin
from .serializers import (
    AdminProfileSerializer, AdminProfileUpdateSerializer,
    VerifiedUserSerializer, PermissionSerializer, SuperAdminSerializer
)
from .permissions import IsSuperAdmin 

from plans_coupens.models import PurchasedPlan, Plan
from django.db.models import Sum, Count
from datetime import timedelta
from django.utils import timezone

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
    Aggregate System Analytics for Super Admin Dashboard.
    """
    permission_classes = [IsSuperAdmin]

    @action(detail=False, methods=['get'])
    def metrics(self, request):
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        
        # 1. Clinic / Subscription Metrics
        total_subscriptions = PurchasedPlan.objects.filter(is_active=True).count()
        new_subscriptions_30d = PurchasedPlan.objects.filter(start_date__gte=thirty_days_ago).count()
        
        # 2. Revenue (Assuming Plan.price is monthly)
        # Note: Summing prices of all active purchased plans
        total_mrr = PurchasedPlan.objects.filter(is_active=True).aggregate(
            total=Sum('plan__price')
        )['total'] or 0.00
        
        # 3. User Growth
        total_users = VerifiedUser.objects.count()
        new_users_30d = VerifiedUser.objects.filter(created_at__gte=thirty_days_ago).count()
        
        # 4. Plan Distribution
        plan_distribution = PurchasedPlan.objects.filter(is_active=True).values(
            'plan__title'
        ).annotate(count=Count('id')).order_by('-count')
        
        return Response({
            "overview": {
                "active_subscriptions": total_subscriptions,
                "new_subscriptions_30d": new_subscriptions_30d,
                "monthly_recurring_revenue": float(total_mrr),
                "total_verified_users": total_users,
                "new_users_30d": new_users_30d
            },
            "plans": [
                {"name": p['plan__title'], "count": p['count']} 
                for p in plan_distribution
            ],
            "timestamp": now.isoformat()
        })
