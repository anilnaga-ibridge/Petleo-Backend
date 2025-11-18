# from django.urls import path

# from .views import RegisterView, LoginView, LogoutView, AdminActionView
# from .views import  RoleCreateView, RoleListView, PermissionCreateView

# from .views import (
#     UserListView,
#     UserDetailView,
#     UserDeleteView,
#     UpdatePasswordView,
#     UserPartialDeleteView
# )

# urlpatterns = [
#     path('register/', RegisterView.as_view(), name='register'),
#     path('login/', LoginView.as_view(), name='login'),
#     path('logout/', LogoutView.as_view(), name='logout'),
#     path('admin-action/', AdminActionView.as_view(), name='admin_action'),
#     # Roles & Permissions
#     path('roles/', RoleListView.as_view()),
#     path('roles/create/', RoleCreateView.as_view()),
#     path('permissions/create/', PermissionCreateView.as_view()),
    
    
    
#     #CRUD operations
#     path('users/', UserListView.as_view(), name='user-list'),
#     path('users/<uuid:id>/', UserDetailView.as_view(), name='user-detail'),
#     path('users/<uuid:id>/delete/', UserDeleteView.as_view(), name='user-delete'),
#     path('users/update-password/', UpdatePasswordView.as_view(), name='update-password'),
#     path('users/partial-delete/', UserPartialDeleteView.as_view(), name='UserPartialDeleteView'),

# ]
# # =======================================================phno otp ============================
# users/urls.py
from django.urls import path, include
from .views import RegisterView, SendOTPView, VerifyOTPView, RefreshTokenView, LogoutView
from . import views
from rest_framework.routers import DefaultRouter
from .views import (
   
    UserViewSet,ResendOTPView,RoleViewSet,PermissionViewSet, SetPinView,
    LoginWithPinView,
    ResetPinView,ChangePinView,
)
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r"roles", RoleViewSet, basename="roles")
router.register(r"permissions", PermissionViewSet, basename="permissions")

urlpatterns = [
    path('api/auth/register/', RegisterView.as_view(), name='auth-register'),
    path('api/auth/send-otp/', SendOTPView.as_view(), name='auth-send-otp'),
    path('api/auth/verify-otp/', VerifyOTPView.as_view(), name='auth-verify-otp'),
    path('api/auth/refresh-token/', RefreshTokenView.as_view(), name='auth-refresh'),
    path('api/auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path("api/auth/resend-otp/", ResendOTPView.as_view(), name="resend_otp"),
    
     path("register-superadmin/", views.register_superadmin, name="register-superadmin"),
     
     
     path("roles/public/", views.public_roles, name="public_roles"),
   
    
    
    # verifyed user CRUD via ViewSet and Router
      path('', include(router.urls)),
      
      
       # --- 🔐 PIN Authentication Routes ---
    path("set-pin/", SetPinView.as_view(), name="set-pin"),  
    # Authenticated user sets a PIN after OTP login

    path("login-with-pin/", LoginWithPinView.as_view(), name="login-with-pin"),
    # Login using PIN (only valid same calendar day)

    path("reset-pin/", ResetPinView.as_view(), name="reset-pin"),
    # Triggers OTP for PIN reset (verify OTP → set new PIN)

    path("change-pin/", ChangePinView.as_view(), name="change-pin"),
    # Authenticated user changes PIN (old PIN + new PIN)
]







