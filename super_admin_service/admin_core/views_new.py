from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AdminProfile, Permission, VerifiedUser
from .permissions import IsSuperAdmin
from .serializers import (
    AdminProfileSerializer,
    AdminProfileUpdateSerializer,
)

# ---------------- Admin Profile Views ---------------- #

class AdminProfileDetailView(APIView):
    """
    Retrieve admin profile by verified_user.auth_user_id
    """
    permission_classes = [IsSuperAdmin]

    def get_object(self, auth_user_id):
        verified_user = get_object_or_404(VerifiedUser, auth_user_id=auth_user_id)
        admin_profile, _ = AdminProfile.objects.get_or_create(verified_user=verified_user)
        return admin_profile

    def get(self, request, auth_user_id):
        admin = self.get_object(auth_user_id)
        serializer = AdminProfileSerializer(admin)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminProfileUpdateView(generics.RetrieveUpdateAPIView):
    """
    Update admin profile
    """
    queryset = AdminProfile.objects.all()
    serializer_class = AdminProfileUpdateSerializer
    permission_classes = [IsSuperAdmin]
    lookup_field = 'verified_user_id'
    lookup_url_kwarg = 'pk'


class AdminProfileDeleteView(APIView):
    """
    Soft delete an admin profile
    """
    permission_classes = [IsSuperAdmin]

    def delete(self, request, pk):
        if not request.user.is_super_admin:
            return Response(
                {"error": "Only SuperAdmins can perform soft deletion"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            admin = AdminProfile.objects.get(pk=pk)
        except AdminProfile.DoesNotExist:
            return Response({"error": "Admin not found"}, status=404)

        admin.is_deleted = True
        admin.activity_status = "inactive"
        admin.save(update_fields=["is_deleted", "activity_status", "updated_at"])
        return Response({
            "message": "Admin soft deleted successfully",
            "deleted_by": request.user.email
        }, status=200)


class AdminStatusToggleView(APIView):
    """
    Toggle admin's activity status
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk):
        try:
            admin = AdminProfile.objects.get(pk=pk)
        except AdminProfile.DoesNotExist:
            return Response({"error": "Admin not found"}, status=404)

        admin.activity_status = "inactive" if admin.activity_status == "active" else "active"
        admin.save(update_fields=["activity_status", "updated_at"])
        return Response({"message": f"Admin set to {admin.activity_status}"}, status=200)


# ---------------- Permission Management ---------------- #

class AdminPermissionManageView(APIView):
    """
    Manage admin permissions - add, remove, or update
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk):
        """Add permissions"""
        try:
            admin = AdminProfile.objects.get(pk=pk)
        except AdminProfile.DoesNotExist:
            return Response({"error": "Admin not found"}, status=404)

        permission_ids = request.data.get("permissions", [])
        permissions = Permission.objects.filter(id__in=permission_ids)
        admin.permissions.add(*permissions)
        return Response({"message": "Permissions added successfully"}, status=200)

    def delete(self, request, pk):
        """Remove permissions"""
        try:
            admin = AdminProfile.objects.get(pk=pk)
        except AdminProfile.DoesNotExist:
            return Response({"error": "Admin not found"}, status=404)

        permission_ids = request.data.get("permissions", [])
        permissions = Permission.objects.filter(id__in=permission_ids)
        admin.permissions.remove(*permissions)
        return Response({"message": "Permissions removed successfully"}, status=200)

    def put(self, request, pk):
        """Replace existing permissions"""
        try:
            admin = AdminProfile.objects.get(pk=pk)
        except AdminProfile.DoesNotExist:
            return Response({"error": "Admin not found"}, status=404)

        permission_ids = request.data.get("permissions", [])
        permissions = Permission.objects.filter(id__in=permission_ids)
        admin.permissions.set(permissions)
        return Response({"message": "Permissions updated successfully"}, status=200)