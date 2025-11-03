
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SuperAdmin, AdminProfile, Permission, VerifiedUser
from .permissions import IsSuperAdmin
from .serializers import (
    AdminProfileSerializer,
    AdminProfileUpdateSerializer,
)

# ---------------- Admin Profile Views ---------------- #




# class AdminProfileListCreateView(generics.ListCreateAPIView):
#     """
#     GET: List all admins (SuperAdmin + Admin can view)
#     POST: Create new admin (SuperAdmin + Admin can create)
#     """
#     queryset = AdminProfile.objects.all()
#     serializer_class = AdminProfileSerializer
#     permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]

#     def perform_create(self, serializer):
#         user = self.request.user
#         role = getattr(user, "role", "").lower()

#         if role not in ["superadmin", "admin"]:
#             raise PermissionDenied("Only SuperAdmins or Admins can create admins.")

#         serializer.save()  # No need for created_by since model doesn't have it



# ✅ View admin details
class AdminProfileDetailView(generics.RetrieveAPIView):
    queryset = AdminProfile.objects.all()
    serializer_class = AdminProfileSerializer
    permission_classes = [IsSuperAdmin]
    lookup_field = 'verified_user_id'
    lookup_url_kwarg = 'auth_user_id'

# ✅ Update admin details
class AdminProfileUpdateView(generics.RetrieveUpdateAPIView):
    queryset = AdminProfile.objects.all()
    serializer_class = AdminProfileUpdateSerializer
    permission_classes = [IsSuperAdmin]
    lookup_field = 'verified_user_id'
    lookup_url_kwarg = 'pk'


# # ✅ Soft Delete Admin
class AdminProfileDeleteView(APIView):
    permission_classes = [IsSuperAdmin]  # Only SuperAdmins can perform soft deletion

    def delete(self, request, pk):
        user = request.user
        if not getattr(user, "is_super_admin", False):
            return Response(
                {"error": "Only SuperAdmins can perform soft deletion"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            admin = AdminProfile.objects.get(pk=pk)
        except AdminProfile.DoesNotExist:
            return Response({"error": "Admin not found"}, status=404)

        # Double-check user role to prevent regular admins from deleting
        if not request.user.is_super_admin:
            return Response(
                {"error": "Only SuperAdmins can perform soft deletion"},
                status=status.HTTP_403_FORBIDDEN
            )

        admin.is_deleted = True
        admin.activity_status = "inactive"
        admin.save(update_fields=["is_deleted", "activity_status", "updated_at"])
        return Response({
            "message": "Admin soft deleted successfully",
            "deleted_by": request.user.email
        }, status=200)


# # ✅ Toggle active/inactive
# class AdminStatusToggleView(APIView):
#     permission_classes = [IsSuperAdmin]

#     def post(self, request, pk):
#         try:
#             admin = AdminProfile.objects.get(pk=pk)
#         except AdminProfile.DoesNotExist:
#             return Response({"error": "Admin not found"}, status=404)

#         admin.activity_status = "inactive" if admin.activity_status == "active" else "active"
#         admin.save(update_fields=["activity_status", "updated_at"])
#         return Response({"message": f"Admin set to {admin.activity_status}"}, status=200)


# # ✅ Manage Permissions (Add/Remove/Update)
# class AdminPermissionManageView(APIView):
#     permission_classes = [IsSuperAdmin]

#     def post(self, request, pk):
#         """Add permissions"""
#         try:
#             admin = AdminProfile.objects.get(pk=pk)
#         except AdminProfile.DoesNotExist:
#             return Response({"error": "Admin not found"}, status=404)

#         permission_ids = request.data.get("permissions", [])
#         permissions = Permission.objects.filter(id__in=permission_ids)
#         admin.permissions.add(*permissions)
#         return Response({"message": "Permissions added successfully"}, status=200)

#     def delete(self, request, pk):
#         """Remove permissions"""
#         try:
#             admin = AdminProfile.objects.get(pk=pk)
#         except AdminProfile.DoesNotExist:
#             return Response({"error": "Admin not found"}, status=404)

#         permission_ids = request.data.get("permissions", [])
#         permissions = Permission.objects.filter(id__in=permission_ids)
#         admin.permissions.remove(*permissions)
#         return Response({"message": "Permissions removed successfully"}, status=200)

#     def put(self, request, pk):
#         """Replace existing permissions"""
#         try:
#             admin = AdminProfile.objects.get(pk=pk)
#         except AdminProfile.DoesNotExist:
#             return Response({"error": "Admin not found"}, status=404)

#         permission_ids = request.data.get("permissions", [])
#         permissions = Permission.objects.filter(id__in=permission_ids)
#         admin.permissions.set(permissions)
#         return Response({"message": "Permissions updated successfully"}, status=200) 


# super_admin/views.py
from rest_framework import generics, status
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from admin_core.models import AdminProfile, VerifiedUser
from .models import SuperAdmin, AdminProfile, Permission
from .serializers import (
    SuperAdminSerializer,
    AdminProfileSerializer,
    AdminProfileUpdateSerializer,
    PermissionSerializer,
)


# ---------------- SuperAdmin Views ---------------- #

class SuperAdminListView(generics.ListAPIView):
    queryset = SuperAdmin.objects.all()
    serializer_class = SuperAdminSerializer


class SuperAdminDetailView(generics.RetrieveAPIView):
    queryset = SuperAdmin.objects.all()
    serializer_class = SuperAdminSerializer
    lookup_field = 'id'


class SuperAdminUpdateView(generics.UpdateAPIView):
    queryset = SuperAdmin.objects.all()
    serializer_class = SuperAdminSerializer
    lookup_field = 'id'


class SuperAdminDeleteView(APIView):
    def delete(self, request, id):
        try:
            superadmin = SuperAdmin.objects.get(id=id)
            superadmin.delete()
            return Response({"message": "SuperAdmin deleted successfully"}, status=200)
        except SuperAdmin.DoesNotExist:
            return Response({"error": "SuperAdmin not found"}, status=404)


# ---------------- Admin Profile Views ---------------- #

class AdminProfileListCreateView(generics.ListCreateAPIView):
    """
    GET: List all admins
    POST: Create new admin (no permission restrictions)
    """
    queryset = AdminProfile.objects.all()
    serializer_class = AdminProfileSerializer

    def perform_create(self, serializer):
        serializer.save()


class AdminProfileUpdateView(generics.RetrieveUpdateAPIView):
    queryset = AdminProfile.objects.all()
    serializer_class = AdminProfileUpdateSerializer


class AdminProfileDeleteView(APIView):
    def delete(self, request, pk):
        try:
            admin = AdminProfile.objects.get(pk=pk)
        except AdminProfile.DoesNotExist:
            return Response({"error": "Admin not found"}, status=404)

        admin.is_deleted = True
        admin.activity_status = "inactive"
        admin.save(update_fields=["is_deleted", "activity_status", "updated_at"])
        return Response({"message": "Admin soft deleted successfully"}, status=200)


class AdminStatusToggleView(APIView):
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

class AdminProfileDetailView(APIView):
    """
    Retrieve, update, or soft-delete AdminProfile by verified_user.auth_user_id
    """

    def get_object(self, auth_user_id):
        verified_user = get_object_or_404(VerifiedUser, auth_user_id=auth_user_id)
        admin_profile, _ = AdminProfile.objects.get_or_create(verified_user=verified_user)
        return admin_profile

    def get(self, request, auth_user_id):
        admin = self.get_object(auth_user_id)
        serializer = AdminProfileSerializer(admin)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, auth_user_id):
        admin = self.get_object(auth_user_id)
        serializer = AdminProfileSerializer(admin, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, auth_user_id):
        admin = self.get_object(auth_user_id)
        admin.is_deleted = True
        admin.activity_status = "inactive"
        admin.save(update_fields=["is_deleted", "activity_status"])
        return Response(
            {"message": "Admin profile soft-deleted successfully."},
            status=status.HTTP_200_OK
        )
