# from django.urls import path
# from .views import (
#     SuperAdminListView,
#     SuperAdminDetailView,
#     SuperAdminUpdateView,
#     SuperAdminDeleteView,
# )

# urlpatterns = [
#     path('superadmins/', SuperAdminListView.as_view(), name='superadmin-list'),
#     path('superadmins/<uuid:id>/', SuperAdminDetailView.as_view(), name='superadmin-detail'),
#     path('superadmins/<uuid:id>/update/', SuperAdminUpdateView.as_view(), name='superadmin-update'),
#     path('superadmins/<uuid:id>/delete/', SuperAdminDeleteView.as_view(), name='superadmin-delete'),
# ]

from django.urls import path
from .views import (
    SuperAdminListView, SuperAdminDetailView, SuperAdminUpdateView, SuperAdminDeleteView,
    AdminProfileListCreateView, AdminProfileUpdateView, AdminProfileDeleteView,
    AdminStatusToggleView, AdminPermissionManageView,AdminProfileDetailView
)

urlpatterns = [
    # ✅ SuperAdmin routes
    path("superadmins/", SuperAdminListView.as_view(), name="superadmin-list"),
    path("superadmins/<uuid:id>/", SuperAdminDetailView.as_view(), name="superadmin-detail"),
    path("superadmins/<uuid:id>/update/", SuperAdminUpdateView.as_view(), name="superadmin-update"),
    path("superadmins/<uuid:id>/delete/", SuperAdminDeleteView.as_view(), name="superadmin-delete"),

    # ✅ Admin management routes
    path("admins/", AdminProfileListCreateView.as_view(), name="admin-list-create"),
    path("admins/<uuid:auth_user_id>/", AdminProfileDetailView.as_view(), name="admin-detail"),
    path("admins/<uuid:pk>/update/", AdminProfileUpdateView.as_view(), name="admin-update"),
    path("admins/<uuid:pk>/delete/", AdminProfileDeleteView.as_view(), name="admin-delete"),
    path("admins/<uuid:pk>/toggle-status/", AdminStatusToggleView.as_view(), name="admin-toggle-status"),
    path("admins/<uuid:pk>/permissions/", AdminPermissionManageView.as_view(), name="admin-permission-manage"),
    path("admins/<uuid:auth_user_id>/", AdminProfileDetailView.as_view(), name="admin-detail"),

]
