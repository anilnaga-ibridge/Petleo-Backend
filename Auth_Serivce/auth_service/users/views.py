# # from rest_framework.views import APIView
# # from rest_framework.response import Response
# # from rest_framework import status
# # from rest_framework.permissions import IsAuthenticated
# # from .serializers import LoginSerializer, RegisterSerializer,UserSerializer
# # from .tokens import get_tokens_for_user
# # from .permissions import HasPermission
# # import requests

# # # --- Registration API ---
# # # class RegisterView(APIView):
# # #     def post(self, request):
# # #         serializer = RegisterSerializer(data=request.data)
# # #         serializer.is_valid(raise_exception=True)
# # #         serializer.save()
# # #         return Response({"message": "User registered successfully!"}, status=status.HTTP_201_CREATED)
# # EMPLOYEE_SERVICE_URL = "http://127.0.0.1:8001/api/employee/register/"  # update to your Employee Service URL

# # # class RegisterView(APIView):
# # #     def post(self, request):
# # #         serializer = UserSerializer(data=request.data)
# # #         if serializer.is_valid():
# # #             user = serializer.save()
            
# # #             # Generate JWT token
# # #             token = get_tokens_for_user(user)['access']

# # #             # Send data to Employee Service
# # #             try:
# # #                 headers = {'Authorization': f'Bearer {token}'}
# # #                 payload = {
# # #                     "user_id": user.id,
# # #                     "username": user.username,
# # #                     "email": user.email
# # #                 }
# # #                 response = requests.post(EMPLOYEE_SERVICE_URL, json=payload, headers=headers)
# # #                 response.raise_for_status()
# # #             except requests.exceptions.RequestException as e:
# # #                 return Response({"error": "Failed to register in Employee Service", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# # #             return Response({
# # #                 "user_id": user.id,
# # #                 "username": user.username,
# # #                 "email": user.email,
# # #                 "token": token
# # #             }, status=status.HTTP_201_CREATED)
        
# # #         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# # class RegisterView(APIView):
# #     def post(self, request):
# #         serializer = UserSerializer(data=request.data)
# #         if serializer.is_valid():
# #             user = serializer.save()
            
# #             # Generate JWT token
# #             token = get_tokens_for_user(user)['access']

# #             # 🔒 Skip sending data to Employee Service for now
# #             # try:
# #             #     headers = {'Authorization': f'Bearer {token}'}
# #             #     payload = {
# #             #         "user_id": user.id,
# #             #         "username": user.username,
# #             #         "email": user.email
# #             #     }
# #             #     response = requests.post(EMPLOYEE_SERVICE_URL, json=payload, headers=headers)
# #             #     response.raise_for_status()
# #             # except requests.exceptions.RequestException as e:
# #             #     return Response({"error": "Failed to register in Employee Service", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# #             return Response({
# #                 "user_id": user.id,
# #                 "username": user.username,
# #                 "email": user.email,
# #                 "token": token
# #             }, status=status.HTTP_201_CREATED)
        
# #         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# # # --- Login API ---
# # class LoginView(APIView):
# #     def post(self, request):
# #         serializer = LoginSerializer(data=request.data)
# #         serializer.is_valid(raise_exception=True)
# #         user = serializer.validated_data['user']
# #         tokens = get_tokens_for_user(user)
# #         return Response(tokens, status=status.HTTP_200_OK)

# # # --- Logout API ---
# # class LogoutView(APIView):
# #     permission_classes = [IsAuthenticated]

# #     def post(self, request):
# #         # increment token_version to revoke old tokens
# #         request.user.token_version += 1
# #         request.user.save(update_fields=["token_version"])
# #         return Response({"message": "Logged out. All old tokens revoked."})

# # # --- Admin Action API ---
# # class AdminActionView(APIView):
# #     permission_classes = [IsAuthenticated, HasPermission]
# #     permission_codename = "delete_user"
# #     validate_ip = True  # enforce IP check

# #     def delete(self, request):
# #         return Response({"message": "Admin delete performed!"})
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.permissions import IsAuthenticated
# from .serializers import LoginSerializer, UserSerializer
# from .tokens import get_tokens_for_user
# from .permissions import HasPermission
# import requests

# # URL of the Employee Service endpoint



# EMPLOYEE_SERVICE_URL = "http://127.0.0.1:8001/api/employee/register/"

# # --- Login API ---
# class LoginView(APIView):
#     def post(self, request):
#         serializer = LoginSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.validated_data['user']

#         tokens = get_tokens_for_user(user)
#         return Response({
#             "user_id": user.id,
#             "username": user.username,
#             "email": user.email,
#             "tokens": tokens
#         }, status=status.HTTP_200_OK)

# # --- Registration API ---
# class RegisterView(APIView):
#     def post(self, request):
#         serializer = UserSerializer(data=request.data)
#         if serializer.is_valid():
#             user = serializer.save()

#             # Generate JWT token
#             token = get_tokens_for_user(user)['access']

#             # Send data to Employee Service
#             # try:
#             #     headers = {'Authorization': f'Bearer {token}'}
#             #     payload = {
#             #         "user_id": user.id,
#             #         "username": user.username,
#             #         "email": user.email
#             #     }
#             #     response = requests.post(EMPLOYEE_SERVICE_URL, json=payload, headers=headers)
#             #     response.raise_for_status()
#             # except requests.exceptions.RequestException as e:
#             #     return Response({"error": "Failed to register in Employee Service", "details": str(e)},
#             #                     status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#             return Response({
#                 "user_id": user.id,
#                 "username": user.username,
#                 "email": user.email,
#                 "token": token
#             }, status=status.HTTP_201_CREATED)

#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# class LogoutView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         request.user.token_version += 1
#         request.user.save(update_fields=["token_version"])
#         return Response({"message": "Logged out. All old tokens revoked."})

# class AdminActionView(APIView):
#     permission_classes = [IsAuthenticated, HasPermission]
#     permission_codename = "delete_user"
#     validate_ip = True  # enforce IP check

#     def delete(self, request):
#         return Response({"message": "Admin delete performed!"})




# ================================================ without kafka ==========================================
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.permissions import IsAuthenticated
# from .serializers import (
#     RegisterSerializer, LoginSerializer, RoleSerializer, RoleCreateSerializer, PermissionSerializer
# )
# from .tokens import get_tokens_for_user
# from .permissions import HasPermission
# from .models import Role, Permission, User
# import requests
# from django.conf import settings

# # --- User APIs ---
# # class RegisterView(APIView):
# #     def post(self, request):
# #         serializer = RegisterSerializer(data=request.data)
# #         serializer.is_valid(raise_exception=True)
# #         user = serializer.save()

# #         token = get_tokens_for_user(user)['access']
# #         return Response({
# #             "user_id": user.id,
# #             "username": user.username,
# #             "email": user.email,
# #             "role": user.role.name if user.role else None,
# #             "token": token
# #         }, status=status.HTTP_201_CREATED)
# # class RegisterView(APIView):
# #     def post(self, request):
# #         serializer = RegisterSerializer(data=request.data)
# #         serializer.is_valid(raise_exception=True)
# #         user = serializer.save()

# #         # Generate JWT token
# #         token = get_tokens_for_user(user)['access']

# #         # Prepare payload to send to Employee Service
# #         payload = {
# #             "user_id": user.id,
# #             "username": user.username,
# #             "email": user.email,
# #             "phone": user.phone if hasattr(user, 'phone') else None,
# #             "token": token
# #         }

# #         # Call the Employee Service API
# #         try:
# #             response = requests.post(
# #                 "http://127.0.0.1:8001/api/employee/register/",  # replace with real URL
# #                 json=payload,
# #                 timeout=5
# #             )
# #             response.raise_for_status()
# #         except requests.RequestException as e:
# #             return Response({
# #                 "error": "Failed to register in Employee Service",
# #                 "details": str(e)
# #             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# #         return Response({
# #             "user_id": user.id,
# #             "username": user.username,
# #             "email": user.email,
# #             "phone": user.phone if hasattr(user, 'phone') else None,
# #             "token": token
# #         }, status=status.HTTP_201_CREATED)

# class RegisterView(APIView):
#     def post(self, request):
#         serializer = RegisterSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.save()

#         # Generate JWT token
#         token = get_tokens_for_user(user)['access']

#         payload = {
#             "user_id": user.id,
#             "username": user.username,
#             "email": user.email,
#             "phone": getattr(user, 'phone', None),
#             "token": str(token),
#         }

#         # ✅ Notify other services
#         errors = []
#         for service_name, url in settings.SERVICE_ENDPOINTS.items():
#             try:
#                 response = requests.post(
#                     url,
#                     json=payload,
#                     headers={"Authorization": f"Bearer {token}"},
#                     timeout=5
#                 )
#                 response.raise_for_status()
#             except requests.RequestException as e:
#                 errors.append({service_name: str(e)})

#         # If some services failed, return partial success
#         if errors:
#             return Response({
#                 "message": "User registered, but some services failed to sync.",
#                 "errors": errors,
#                 "user": payload
#             }, status=status.HTTP_207_MULTI_STATUS)

#         return Response({
#             "message": "User registered successfully across all services.",
#             "user": payload
#         }, status=status.HTTP_201_CREATED)
        
        
# class LoginView(APIView):
#     def post(self, request):
#         serializer = LoginSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.validated_data['user']
#         tokens = get_tokens_for_user(user)
#         return Response(tokens, status=status.HTTP_200_OK)


# class LogoutView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         request.user.token_version += 1
#         request.user.save(update_fields=["token_version"])
#         return Response({"message": "Logged out. All old tokens revoked."})


# # --- Role & Permission Management ---
# class PermissionCreateView(APIView):
#     permission_classes = [IsAuthenticated]
#     permission_codename = 'create_permission'

#     def post(self, request):
#         serializer = PermissionSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         permission = serializer.save()
#         return Response(PermissionSerializer(permission).data, status=status.HTTP_201_CREATED)


# class RoleCreateView(APIView):
#     permission_classes = [IsAuthenticated]
#     permission_codename = 'create_role'

#     def post(self, request):
#         serializer = RoleCreateSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         role = serializer.save()
#         return Response(RoleSerializer(role).data, status=status.HTTP_201_CREATED)


# class RoleListView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         roles = Role.objects.all()
#         serializer = RoleSerializer(roles, many=True)
#         return Response(serializer.data)

# class AdminActionView(APIView):
#     permission_classes = [IsAuthenticated, HasPermission]
#     permission_codename = "delete_user"

#     def delete(self, request):
#         return Response({"message": "Admin action performed!"})





# ====================================================with kafka===================================
# from rest_framework.views import APIView


# from rest_framework.permissions import IsAuthenticated
# from .serializers import (
#     RegisterSerializer, LoginSerializer, RoleSerializer, RoleCreateSerializer, PermissionSerializer
# )
# from .tokens import get_tokens_for_user
# from .permissions import HasPermission
# from .models import Role, Permission, User
# import requests
# from django.conf import settings
# from .kafka_producer import publish_user_created_event


# from rest_framework import generics, status
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated
# from django.contrib.auth import get_user_model
# from django.contrib.auth.hashers import check_password
# from .serializers import UserSerializer, UpdatePasswordSerializer
# from .email_utils import send_password_email
# from django.conf import settings

# from rest_framework.views import APIView



# # --- User APIs ---
# # class RegisterView(APIView):
# #     def post(self, request):
# #         serializer = RegisterSerializer(data=request.data)
# #         serializer.is_valid(raise_exception=True)
# #         user = serializer.save()

# #         token = get_tokens_for_user(user)['access']
# #         return Response({
# #             "user_id": user.id,
# #             "username": user.username,
# #             "email": user.email,
# #             "role": user.role.name if user.role else None,
# #             "token": token
# #         }, status=status.HTTP_201_CREATED)
# # class RegisterView(APIView):
# #     def post(self, request):
# #         serializer = RegisterSerializer(data=request.data)
# #         serializer.is_valid(raise_exception=True)
# #         user = serializer.save()

# #         # Generate JWT token
# #         token = get_tokens_for_user(user)['access']

# #         # Prepare payload to send to Employee Service
# #         payload = {
# #             "user_id": user.id,
# #             "username": user.username,
# #             "email": user.email,
# #             "phone": user.phone if hasattr(user, 'phone') else None,
# #             "token": token
# #         }

# #         # Call the Employee Service API
# #         try:
# #             response = requests.post(
# #                 "http://127.0.0.1:8001/api/employee/register/",  # replace with real URL
# #                 json=payload,
# #                 timeout=5
# #             )
# #             response.raise_for_status()
# #         except requests.RequestException as e:
# #             return Response({
# #                 "error": "Failed to register in Employee Service",
# #                 "details": str(e)
# #             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# #         return Response({
# #             "user_id": user.id,
# #             "username": user.username,
# #             "email": user.email,
# #             "phone": user.phone if hasattr(user, 'phone') else None,
# #             "token": token
# #         }, status=status.HTTP_201_CREATED)

# # class RegisterView(APIView):
# #     def post(self, request):
# #         serializer = RegisterSerializer(data=request.data)
# #         serializer.is_valid(raise_exception=True)
# #         user = serializer.save()
# #         token = get_tokens_for_user(user)['access']

# #         payload = {
# #             "user_id": user.id,
# #             "username": user.username,
# #             "email": user.email,
# #             "phone": getattr(user, 'phone', None),
# #             "token": str(token)
# #         }

# #         # Publish event to Kafka
# #         publish_user_created_event(payload)

# #         return Response({"user": payload}, status=status.HTTP_201_CREATED)


# # class RegisterView(APIView):
# #     def post(self, request):
# #         serializer = RegisterSerializer(data=request.data)
# #         serializer.is_valid(raise_exception=True)
# #         user = serializer.save()

# #         # Generate JWT token
# #         token = get_tokens_for_user(user)['access']

# #         # Prepare payload
# #         payload = {
# #             "user_id": user.id,
# #             "username": user.username,
# #             "email": user.email,
# #             "phone": getattr(user, 'phone', None),
# #             "token": str(token)
# #         }

# #         # ✅ Send message to Kafka
# #         publish_user_created_event(payload)

# #         return Response({
# #             "message": "User registered successfully.",
# #             "user": payload
# #         }, status=status.HTTP_201_CREATED)


# # class RegisterView(APIView):
# #     def post(self, request):
# #         serializer = RegisterSerializer(data=request.data)
# #         serializer.is_valid(raise_exception=True)
# #         user = serializer.save()  # Save only auth-required fields

# #         # Generate JWT token
# #         token = get_tokens_for_user(user)['access']

# #         # Base auth data to send
# #         auth_data = {
# #             "auth_user_id": str(user.id),
# #             "username": user.username,
# #             "email": user.email,
# #             "token": str(token),
# #             "role": request.data.get("role")  # optional, default can be set in frontend
# #         }

# #         # Include all extra fields dynamically
# #         extra_fields = {k: v for k, v in request.data.items()
# #                         if k not in ["username", "email", "password", "role"]}

# #         payload = {**auth_data, **extra_fields}

# #         # Send payload to Kafka
# #         publish_user_created_event(payload)

# #         return Response({
# #             "message": "User registered successfully.",
# #             "user": payload
# #         }, status=status.HTTP_201_CREATED)

# # class RegisterView(APIView):
# #     def post(self, request):
# #         serializer = RegisterSerializer(data=request.data)
# #         serializer.is_valid(raise_exception=True)
# #         user = serializer.save()

# #         token = get_tokens_for_user(user)['access']

# #         # Collect extra fields dynamically
# #         extra_fields = {k: v for k, v in request.data.items() 
# #                         if k not in ["username", "email", "password", "role"]}

# #         # Publish to Kafka
# #         publish_user_created_event(user, extra_fields=extra_fields, role=request.data.get("role"))

# #         return Response({
# #             "message": "User registered successfully.",
# #             "user": {
# #                 "auth_user_id": str(user.id),
# #                 "username": user.username,
# #                 "email": user.email,
# #                 "role": request.data.get("role")
# #             }
# #         }, status=201)
        
        
# class LoginView(APIView):
#     def post(self, request):
#         serializer = LoginSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.validated_data['user']
#         tokens = get_tokens_for_user(user)
#         return Response(tokens, status=status.HTTP_200_OK)


# class LogoutView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         request.user.token_version += 1
#         request.user.save(update_fields=["token_version"])
#         return Response({"message": "Logged out. All old tokens revoked."})


# # --- Role & Permission Management ---
# class PermissionCreateView(APIView):
#     permission_classes = [IsAuthenticated]
#     permission_codename = 'create_permission'

#     def post(self, request):
#         serializer = PermissionSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         permission = serializer.save()
#         return Response(PermissionSerializer(permission).data, status=status.HTTP_201_CREATED)


# class RoleCreateView(APIView):
#     permission_classes = [IsAuthenticated]
#     permission_codename = 'create_role'

#     def post(self, request):
#         serializer = RoleCreateSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         role = serializer.save()
#         return Response(RoleSerializer(role).data, status=status.HTTP_201_CREATED)


# class RoleListView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         roles = Role.objects.all()
#         serializer = RoleSerializer(roles, many=True)
#         return Response(serializer.data)

# class AdminActionView(APIView):
#     permission_classes = [IsAuthenticated, HasPermission]
#     permission_codename = "delete_user"

#     def delete(self, request):
#         return Response({"message": "Admin action performed!"})
    




# # =============================================================



# # ✅ Get all users
# class UserListView(generics.ListAPIView):
#     queryset = User.objects.all()
#     serializer_class = UserSerializer
#     permission_classes = [IsAuthenticated]
    


# # ✅ Get user by ID
# class UserDetailView(generics.RetrieveAPIView):
#     queryset = User.objects.all()
#     serializer_class = UserSerializer
#     permission_classes = [IsAuthenticated]
#     lookup_field = 'id'


# class UserDeleteView(APIView):
#     def delete(self, request, id):
#         try:
#             user = User.objects.get(id=id)
#             user_data = {
#                 "id": str(user.id),
#                 "username": user.username,
#                 "email": user.email,
#                 "role": str(user.role.id) if user.role else None
#             }
#             user.delete()
#             return Response(
#                 {"message": "User deleted successfully", "deleted_user": user_data},
#                 status=status.HTTP_200_OK
#             )
#         except User.DoesNotExist:
#             return Response(
#                 {"error": "User not found"},
#                 status=status.HTTP_404_NOT_FOUND
#             )




# class UpdatePasswordView(APIView):
#     permission_classes = [IsAuthenticated]

#     def put(self, request, *args, **kwargs):
#         serializer = UpdatePasswordSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         old_password = serializer.validated_data.get("old_password")
#         new_password = serializer.validated_data.get("new_password")

#         user = request.user

#         if not check_password(old_password, user.password):
#             return Response({"error": "Old password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

#         user.set_password(new_password)
#         user.save()
#         return Response({"message": "Password updated successfully"}, status=status.HTTP_200_OK)





# class UserPartialDeleteView(APIView):
#     """
#     Soft delete a user by marking them inactive instead of removing from DB.
#     """
#     def patch(self, request, id):
#         try:
#             user = User.objects.get(id=id)
#             user.is_active = False  # mark as inactive
#             user.save(update_fields=['is_active'])

#             return Response(
#                 {
#                     "message": "User deactivated successfully",
#                     "user": {
#                         "id": str(user.id),
#                         "username": user.username,
#                         "email": user.email,
#                         "role": str(user.role.id) if user.role else None,
#                         "is_active": user.is_active
#                     }
#                 },
#                 status=status.HTTP_200_OK
#             )

#         except User.DoesNotExist:
#             return Response(
#                 {"error": "User not found"},
#                 status=status.HTTP_404_NOT_FOUND
#             )
            

# User = get_user_model()

# class RegisterView(APIView):
#     def post(self, request):
#         serializer = RegisterSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.save()
        
#         # Check if password was generated (not provided in request)
#         password_was_generated = not request.data.get('password')
#         generated_password = getattr(user, 'generated_password', None)
        
#         # Send email if password was generated
#         email_sent = False
#         if password_was_generated and generated_password:
#             # Get email credentials from request body OR fall back to settings
#             sender_email = request.data.get('sender_email')
#             sender_password = request.data.get('sender_password')
            
#             # If no sender credentials in request, use settings
#             if not sender_email or not sender_password:
#                 sender_email = getattr(settings, 'EMAIL_HOST_USER', None)
#                 sender_password = getattr(settings, 'EMAIL_HOST_PASSWORD', None)
            
#             # Check if we have valid email credentials (skip check for console mode)
#             using_console = settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend'
            
#             if using_console:
#                 # Console mode - always send
#                 email_sent = send_password_email(
#                     user_email=user.email, 
#                     username=user.username, 
#                     password=generated_password,
#                     sender_email=None,
#                     sender_password=None
#                 )
#             elif not sender_email or not sender_password or sender_password in ['your-16-character-app-password-here', 'replace-with-your-real-app-password']:
#                 print("Warning: Password generated but no valid email credentials available.")
#                 print("Either:")
#                 print("1. Include 'sender_email' and 'sender_password' in request body, OR")
#                 print("2. Update EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env file")
#                 email_sent = False
#             else:
#                 # SMTP mode with valid credentials
#                 email_sent = send_password_email(
#                     user_email=user.email, 
#                     username=user.username, 
#                     password=generated_password,
#                     sender_email=sender_email,
#                     sender_password=sender_password
#                 )
#                 if not email_sent:
#                     print(f"Warning: Failed to send password email to {user.email}")
        
#         token = get_tokens_for_user(user)['access']
#         extra_fields = {k:v for k,v in request.data.items() if k not in ['username','email','password','role','sender_email','sender_password']}
#         publish_user_created_event(user, extra_fields, request.data.get('role'))
        
#         response_data = {
#             'message': 'User registered successfully',
#             'user': {
#                 'auth_user_id': str(user.id), 
#                 'username': user.username,
#                 'email': user.email, 
#                 'role': request.data.get('role')
#             }
#         }
        
#         # Add additional info if password was generated
#         if password_was_generated:
#             if email_sent:
#                 response_data['password_info'] = {
#                     'generated': True,
#                     'email_sent': True,
#                     'message': 'Password generated and sent to your email address successfully'
#                 }
#             else:
#                 response_data['password_info'] = {
#                     'generated': True,
#                     'email_sent': False,
#                     'generated_password': generated_password,  # Include password in response since email failed
#                     'message': 'Password generated but email sending failed. Use the password above to login.'
#                 }
        
#         return Response(response_data, status=201)


# ============================ phno otp ===========================================
# # auth_service/views.py
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from django.utils import timezone
# from datetime import timedelta
# from django.contrib.auth import get_user_model
# from .serializers import RegisterSerializer, SendOTPSerializer, VerifyOTPSerializer
# from .models import OTP, User
# from .utils import generate_numeric_otp, send_sms_via_provider
# from .tokens import get_tokens_for_user
# from .kafka_producer import publish_user_created_event

# User = get_user_model()

# OTP_TTL_MINUTES = 10

# class RegisterView(APIView):
#     """
#     Register user (create auth user) and send OTP for verification.
#     Payload:
#     {
#       "full_name": "Anil Kumar",
#       "email": "anil@example.com",
#       "phone_number": "9876543210",
#       "role": "grooming"
#     }
#     """
#     def post(self, request):
#         serializer = RegisterSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.save()

#         # Generate OTP for 'register' purpose
#         otp_code = generate_numeric_otp()
#         expires_at = timezone.now() + timedelta(minutes=OTP_TTL_MINUTES)
#         OTP.objects.create(phone_number=user.phone_number, otp=otp_code, purpose='register', expires_at=expires_at)

#         # send SMS (console or provider)
#         message = f"Your registration OTP is: {otp_code} (valid {OTP_TTL_MINUTES} minutes)"
#         sms_ok = send_sms_via_provider(user.phone_number, message)

#         # publish created event (you may want to include full profile payload)
#         payload = {
#             "auth_user_id": str(user.id),
#             "phone_number": user.phone_number,
#             "email": user.email,
#             "role": user.role.name if user.role else None,
#         }
#         publish_user_created_event(payload)

#         # return helpful response (don't send OTP in prod when using SMS provider)
#         response = {
#             "message": "User registered. OTP sent for verification.",
#             "phone_number": user.phone_number,
#             "sms_sent": sms_ok,
#         }
#         # if using console backend, include otp for easy testing
#         if getattr(user, 'phone_number', None) and getattr(__import__('django.conf').conf.settings, 'SMS_BACKEND', 'console') == 'console':
#             response['otp'] = otp_code

#         return Response(response, status=status.HTTP_201_CREATED)


# class SendOTPView(APIView):
#     """
#     Send OTP to phone_number for purposes: register / login / verify
#     Payload:
#       { "phone_number": "9876543210", "purpose": "login" }
#     """
#     def post(self, request):
#         serializer = SendOTPSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         phone = serializer.validated_data['phone_number']
#         purpose = serializer.validated_data.get('purpose', 'login')

#         # if purpose == 'login' ensure user exists
#         if purpose == 'login':
#             if not User.objects.filter(phone_number=phone).exists():
#                 return Response({"detail": "Phone number not registered. Please register first."}, status=status.HTTP_400_BAD_REQUEST)

#         otp_code = generate_numeric_otp()
#         expires_at = timezone.now() + timedelta(minutes=OTP_TTL_MINUTES)
#         OTP.objects.create(phone_number=phone, otp=otp_code, purpose=purpose, expires_at=expires_at)

#         message = f"Your OTP is: {otp_code} (valid {OTP_TTL_MINUTES} minutes)"
#         sms_ok = send_sms_via_provider(phone, message)

#         resp = {"message": "OTP sent", "phone_number": phone, "sms_sent": sms_ok}
#         if getattr(__import__('django.conf').conf.settings, 'SMS_BACKEND', 'console') == 'console':
#             resp['otp'] = otp_code
#         return Response(resp, status=status.HTTP_200_OK)


# class VerifyOTPView(APIView):
#     """
#     Verify OTP and (for login) return JWT token + user info
#     Payload:
#       { "phone_number": "9876543210", "otp": "123456", "purpose": "login" }
#     """
#     def post(self, request):
#         serializer = VerifyOTPSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         phone = serializer.validated_data['phone_number']
#         otp_val = serializer.validated_data['otp']
#         purpose = serializer.validated_data.get('purpose', 'login')

#         otp_qs = OTP.objects.filter(phone_number=phone, purpose=purpose, used=False).order_by('-created_at')
#         if not otp_qs.exists():
#             return Response({"detail": "OTP not found. Request a new OTP."}, status=status.HTTP_400_BAD_REQUEST)

#         latest = otp_qs.first()
#         if latest.is_expired():
#             return Response({"detail": "OTP expired. Request a new OTP."}, status=status.HTTP_400_BAD_REQUEST)

#         if latest.otp != otp_val:
#             return Response({"detail": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

#         # mark used
#         latest.used = True
#         latest.save(update_fields=['used'])

#         # if purpose == 'register' we can mark user as verified (if user exists)
#         if purpose == 'register':
#             try:
#                 user = User.objects.get(phone_number=phone)
#                 user.is_active = True
#                 user.is_verified = True if hasattr(user, 'is_verified') else True
#                 user.save(update_fields=['is_active'])
#                 return Response({"message": "Phone verified. You can now login."}, status=status.HTTP_200_OK)
#             except User.DoesNotExist:
#                 return Response({"detail": "User not found for phone. Please register."}, status=status.HTTP_404_NOT_FOUND)

#         # purpose == 'login' -> generate JWT
#         if purpose == 'login':
#             try:
#                 user = User.objects.get(phone_number=phone)
#             except User.DoesNotExist:
#                 return Response({"detail": "Phone number not registered."}, status=status.HTTP_404_NOT_FOUND)

#             # Build token
#             tokens = get_tokens_for_user(user)
#             return Response({
#                 "message": "OTP verified. Login successful.",
#                 "tokens": tokens,
#                 "user": {
#                     "user_id": str(user.id),
#                     "phone_number": user.phone_number,
#                     "full_name": user.full_name,
#                     "role": user.role.name if user.role else None
#                 }
#             }, status=status.HTTP_200_OK)

#         # generic success for other purposes
#         return Response({"message": "OTP verified."}, status=status.HTTP_200_OK)



# auth_service/views.py
# # users/views.py
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status, permissions
# from django.utils import timezone
# from datetime import timedelta
# from django.conf import settings
# from django.contrib.auth import get_user_model

# from .serializers import RegisterSerializer, SendOTPSerializer, VerifyOTPSerializer, UserSerializer
# from .models import OTP, StoredRefreshToken
# from .utils import create_otp_session, get_otp_session, increment_session_attempts, delete_otp_session, send_sms_via_provider, increment_rate_limit
# from .tokens import get_tokens_for_user, verify_and_rotate_refresh_token
# from .kafka_producer import publish_user_created_event
# from .kafka_producer import publish_user_event 


# User = get_user_model()
# OTP_TTL_MINUTES = int(getattr(settings, 'OTP_TTL_SECONDS', 600)) // 60

# STATIC_SUPERADMIN_PHONE = getattr(settings, 'STATIC_SUPERADMIN_PHONE', None)
# STATIC_SUPERADMIN_OTP = getattr(settings, 'STATIC_SUPERADMIN_OTP', None)

# RATE_LIMIT_WINDOW = getattr(settings, 'OTP_RATE_LIMIT_WINDOW_SECONDS', 3600)  # e.g., per hour
# RATE_LIMIT_MAX = getattr(settings, 'OTP_RATE_LIMIT_MAX_PER_WINDOW', 5)

# class RegisterView(APIView):
#     """
#     Register user and create OTP session (returns session_id).
#     """
#     def post(self, request):
#         serializer = RegisterSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.save()

#         # rate limit by phone
#         phone = user.phone_number
#         allowed = increment_rate_limit(phone, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX)
#         if not allowed:
#             return Response({"detail": "Too many OTP requests for this phone. Try later."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

#         session_id, otp = create_otp_session(phone, purpose='register')
#         message = f"Your registration OTP is: {otp} (valid {OTP_TTL_MINUTES} minutes)"
#         sms_ok = send_sms_via_provider(phone, message)

#         # publish event (user created)
#         payload = {
#             "auth_user_id": str(user.id),
#             "phone_number": phone,
#             "email": user.email,
#             "role": user.role.name if user.role else None,
#         }
#         publish_user_created_event(payload)

#         response = {
#             "message": "User registered. OTP sent for verification.",
#             "session_id": session_id,
#             "sms_sent": sms_ok,
#         }
#         if getattr(settings, 'SMS_BACKEND', 'console') == 'console':
#             response['otp'] = otp
#         return Response(response, status=status.HTTP_201_CREATED)

# class SendOTPView(APIView):
#     """
#     Endpoint to request OTP for login (returns session_id).
#     """
#     def post(self, request):
#         serializer = SendOTPSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         phone = serializer.validated_data['phone_number']
#         purpose = serializer.validated_data.get('purpose', 'login')

#         # superadmin dev static override
#         if STATIC_SUPERADMIN_PHONE and phone == STATIC_SUPERADMIN_PHONE and purpose == 'login':
#             return Response({
#                 "message": "Static OTP for super admin (dev).",
#                 "session_id": "static-superadmin-session",
#                 "sms_sent": True,
#                 "otp": STATIC_SUPERADMIN_OTP
#             }, status=status.HTTP_200_OK)

#         # if login, ensure user exists
#         if purpose == 'login' and not User.objects.filter(phone_number=phone).exists():
#             return Response({"detail": "Phone number not registered. Please register first."}, status=status.HTTP_400_BAD_REQUEST)

#         # rate limit
#         allowed = increment_rate_limit(phone, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX)
#         if not allowed:
#             return Response({"detail": "Too many OTP requests for this phone. Try later."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

#         session_id, otp = create_otp_session(phone, purpose=purpose)
#         message = f"Your OTP is: {otp} (valid {OTP_TTL_MINUTES} minutes)"
#         sms_ok = send_sms_via_provider(phone, message)

#         resp = {"message": "OTP sent", "session_id": session_id, "sms_sent": sms_ok}
#         if getattr(settings, 'SMS_BACKEND', 'console') == 'console':
#             resp['otp'] = otp
#         return Response(resp, status=status.HTTP_200_OK)

# # class VerifyOTPView(APIView):
# #     """
# #     Verify OTP by session_id + otp. For login, return JWT + refresh.
# #     """
# #     def post(self, request):
# #         serializer = VerifyOTPSerializer(data=request.data)
# #         serializer.is_valid(raise_exception=True)
# #         session_id = serializer.validated_data['session_id']
# #         provided_otp = serializer.validated_data['otp']

# #         # handle static superadmin session
# #         if session_id == "static-superadmin-session":
# #             if provided_otp == STATIC_SUPERADMIN_OTP:
# #                 try:
# #                     user = User.objects.get(phone_number=STATIC_SUPERADMIN_PHONE)
# #                 except User.DoesNotExist:
# #                     return Response({"detail": "Super Admin not found in DB. Create manually."}, status=status.HTTP_404_NOT_FOUND)
# #                 tokens = get_tokens_for_user(user, request=request)
# #                 return Response({
# #                     "message": "Super Admin login successful.",
# #                     "tokens": tokens,
# #                     "user": {
# #                         "user_id": str(user.id),
# #                         "phone_number": user.phone_number,
# #                         "full_name": user.full_name,
# #                         "role": user.role.name if user.role else None
# #                     }
# #                 }, status=status.HTTP_200_OK)
# #             else:
# #                 return Response({"detail": "Invalid OTP for super admin."}, status=status.HTTP_400_BAD_REQUEST)

# #         session = get_otp_session(session_id)
# #         if not session:
# #             return Response({"detail": "Invalid or expired session. Request new OTP."}, status=status.HTTP_400_BAD_REQUEST)

# #         # check purpose
# #         phone = session.get('phone_number')
# #         purpose = session.get('purpose')

# #         # Check allowed attempts (example max 5)
# #         attempts = session.get('attempts', 0)
# #         if attempts >= 5:
# #             delete_otp_session(session_id)
# #             return Response({"detail": "Too many attempts. Request a new OTP."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

# #         if session.get('otp') != provided_otp:
# #             increment_session_attempts(session_id)
# #             return Response({"detail": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

# #         # OTP valid -> delete session
# #         delete_otp_session(session_id)

# #         # For register purpose: activate the user
# #         if purpose == 'register':
# #             try:
# #                 user = User.objects.get(phone_number=phone)
# #                 user.is_active = True
# #                 # optional: set a flag is_verified if you have it
# #                 if hasattr(user, 'is_verified'):
# #                     try:
# #                         user.is_verified = True
# #                     except Exception:
# #                         pass
# #                 user.save(update_fields=['is_active'])
# #                 return Response({"message": "Phone verified. You can now login."}, status=status.HTTP_200_OK)
# #             except User.DoesNotExist:
# #                 return Response({"detail": "User not found for phone. Please register."}, status=status.HTTP_404_NOT_FOUND)

# #         # For login purpose: issue tokens
# #         if purpose == 'login':
# #             try:
# #                 user = User.objects.get(phone_number=phone)
# #             except User.DoesNotExist:
# #                 return Response({"detail": "Phone number not registered."}, status=status.HTTP_404_NOT_FOUND)

# #             tokens = get_tokens_for_user(user, request=request)
# #             return Response({
# #                 "message": "OTP verified. Login successful.",
# #                 "tokens": tokens,
# #                 "user": {
# #                     "user_id": str(user.id),
# #                     "phone_number": user.phone_number,
# #                     "full_name": user.full_name,
# #                     "role": user.role.name if user.role else None
# #                 }
# #             }, status=status.HTTP_200_OK)

# #         return Response({"message": "OTP verified."}, status=status.HTTP_200_OK)


# class VerifyOTPView(APIView):
#     """
#     Verify OTP by session_id + otp.
#     For register → activate user & send Kafka event.
#     For login → return JWT tokens.
#     """

#     def post(self, request):
#         serializer = VerifyOTPSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         session_id = serializer.validated_data['session_id']
#         provided_otp = serializer.validated_data['otp']

#         # ✅ Handle SuperAdmin special case
#         if session_id == "static-superadmin-session":
#             if provided_otp == STATIC_SUPERADMIN_OTP:
#                 try:
#                     user = User.objects.get(phone_number=STATIC_SUPERADMIN_PHONE)
#                 except User.DoesNotExist:
#                     return Response({"detail": "Super Admin not found in DB. Create manually."}, status=status.HTTP_404_NOT_FOUND)

#                 tokens = get_tokens_for_user(user, request=request)
#                 return Response({
#                     "message": "Super Admin login successful.",
#                     "tokens": tokens,
#                     "user": {
#                         "user_id": str(user.id),
#                         "phone_number": user.phone_number,
#                         "full_name": user.full_name,
#                         "role": user.role.name if user.role else None,
#                         "email": user.email
#                     }
#                 }, status=status.HTTP_200_OK)
#             else:
#                 return Response({"detail": "Invalid OTP for super admin."}, status=status.HTTP_400_BAD_REQUEST)

#         # ✅ Normal users
#         session = get_otp_session(session_id)
#         if not session:
#             return Response({"detail": "Invalid or expired session. Request new OTP."}, status=status.HTTP_400_BAD_REQUEST)

#         phone = session.get('phone_number')
#         purpose = session.get('purpose')
#         attempts = session.get('attempts', 0)

#         # Limit attempts
#         if attempts >= 5:
#             delete_otp_session(session_id)
#             return Response({"detail": "Too many attempts. Request a new OTP."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

#         if session.get('otp') != provided_otp:
#             increment_session_attempts(session_id)
#             return Response({"detail": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

#         # ✅ OTP valid
#         delete_otp_session(session_id)

#         # ✅ Registration verification
#         if purpose == 'register':
#             try:
#                 user = User.objects.get(phone_number=phone)
#                 user.is_active = True
#                 if hasattr(user, 'is_verified'):
#                     user.is_verified = True
#                 user.save(update_fields=['is_active'])

#                 # 🔥 Publish Kafka event
#                 user_data = {
#                     "user_id": str(user.id),
#                     "phone_number": user.phone_number,
#                     "full_name": user.full_name,
#                     "role": user.role.name if user.role else None,
#                     "permissions": [p.codename for p in user.role.permissions.all()] if user.role else []
#                 }
#                 publish_user_event("USER_VERIFIED", user_data)

#                 return Response({"message": "Phone verified. You can now login."}, status=status.HTTP_200_OK)
#             except User.DoesNotExist:
#                 return Response({"detail": "User not found for phone. Please register."}, status=status.HTTP_404_NOT_FOUND)

#         # ✅ Login purpose
#         if purpose == 'login':
#             try:
#                 user = User.objects.get(phone_number=phone)
#             except User.DoesNotExist:
#                 return Response({"detail": "Phone number not registered."}, status=status.HTTP_404_NOT_FOUND)

#             tokens = get_tokens_for_user(user, request=request)
#             return Response({
#                 "message": "OTP verified. Login successful.",
#                 "tokens": tokens,
#                 "user": {
#                     "user_id": str(user.id),
#                     "phone_number": user.phone_number,
#                     "full_name": user.full_name,
#                     "role": user.role.name if user.role else None,
#                     "permissions": [p.codename for p in user.role.permissions.all()] if user.role else []
#                 }
#             }, status=status.HTTP_200_OK)

#         return Response({"message": "OTP verified."}, status=status.HTTP_200_OK)

# class RefreshTokenView(APIView):
#     """
#     Accept opaque refresh token, rotate and return new access + refresh.
#     """
#     def post(self, request):
#         token = request.data.get('refresh')
#         if not token:
#             return Response({"detail": "Refresh token required."}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             user, access, new_refresh = verify_and_rotate_refresh_token(token, request=request)
#         except ValueError as e:
#             return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

#         return Response({
#             "access": access,
#             "refresh": new_refresh
#         }, status=status.HTTP_200_OK)

# class LogoutView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request):
#         # optional: revoke provided refresh token or all tokens
#         refresh_plain = request.data.get('refresh')
#         if refresh_plain:
#             from .tokens import _hash_token
#             token_hash = _hash_token(refresh_plain)
#             StoredRefreshToken.objects.filter(token_hash=token_hash).update(revoked=True)

#         # revoke all tokens for user (force logout everywhere) option
#         if request.data.get('revoke_all'):
#             StoredRefreshToken.objects.filter(user=request.user).update(revoked=True)

#         # increment token_version to invalidate existing access JWTs if you check token_version in JWT
#         request.user.token_version = (request.user.token_version or 0) + 1
#         request.user.save(update_fields=['token_version'])
#         return Response({"message": "Logged out. Tokens revoked."}, status=status.HTTP_200_OK)
# import logging
# from datetime import timedelta
# from django.utils import timezone
# from django.conf import settings
# from django.contrib.auth import get_user_model

# from rest_framework import status, permissions
# from rest_framework.response import Response
# from rest_framework.views import APIView






# from rest_framework.decorators import api_view

# from .kafka_producer import publish_event 
# from .models import User, Role
# import uuid
# from .serializers import RegisterSerializer, SendOTPSerializer, VerifyOTPSerializer
# from .models import OTP, StoredRefreshToken
# from .utils import (
#     create_otp_session,
#     get_otp_session,
#     increment_session_attempts,
#     delete_otp_session,
#     send_sms_via_provider,
#     increment_rate_limit,
# )
# from .tokens import get_tokens_for_user, verify_and_rotate_refresh_token
# from .kafka_producer import publish_user_created_event, publish_user_event

# User = get_user_model()
# logger = logging.getLogger(__name__)

# # Settings constants
# OTP_TTL_MINUTES = int(getattr(settings, 'OTP_TTL_SECONDS', 600)) // 60
# RATE_LIMIT_WINDOW = getattr(settings, 'OTP_RATE_LIMIT_WINDOW_SECONDS', 3600)
# RATE_LIMIT_MAX = getattr(settings, 'OTP_RATE_LIMIT_MAX_PER_WINDOW', 5)
# STATIC_SUPERADMIN_PHONE = getattr(settings, 'STATIC_SUPERADMIN_PHONE', None)
# STATIC_SUPERADMIN_OTP = getattr(settings, 'STATIC_SUPERADMIN_OTP', None)


# # ---------------------- REGISTER ----------------------
# class RegisterView(APIView):
#     """
#     Register user and create OTP session (returns session_id).
#     """
#     def post(self, request):
#         serializer = RegisterSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.save()

#         # Rate limit by phone
#         phone = user.phone_number
#         allowed = increment_rate_limit(phone, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX)
#         if not allowed:
#             return Response(
#                 {"detail": "Too many OTP requests for this phone. Try again later."},
#                 status=status.HTTP_429_TOO_MANY_REQUESTS,
#             )

#         # Create OTP
#         session_id, otp = create_otp_session(phone, purpose='register')
#         message = f"Your registration OTP is: {otp} (valid {OTP_TTL_MINUTES} minutes)"
#         sms_ok = send_sms_via_provider(phone, message)

#         # Kafka event: user created
#         payload = {
#             "auth_user_id": str(user.id),
#             "phone_number": phone,
#             "email": user.email,
#             "full_name": user.full_name,
#             "role": user.role.name if user.role else None,
#         }
#         publish_user_created_event(payload)

#         # Response
#         response = {
#             "message": "User registered. OTP sent for verification.",
#             "session_id": session_id,
#             "sms_sent": sms_ok,
#         }
#         if getattr(settings, 'SMS_BACKEND', 'console') == 'console':
#             response['otp'] = otp

#         return Response(response, status=status.HTTP_201_CREATED)


# # ---------------------- SEND OTP ----------------------
# class SendOTPView(APIView):
#     """
#     Request OTP for login (returns session_id).
#     """
#     def post(self, request):
#         serializer = SendOTPSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         phone = serializer.validated_data['phone_number']
#         purpose = serializer.validated_data.get('purpose', 'login')

#         # Static SuperAdmin OTP (for dev/test)
#         if STATIC_SUPERADMIN_PHONE and phone == STATIC_SUPERADMIN_PHONE and purpose == 'login':
#             return Response({
#                 "message": "Static OTP for super admin (dev).",
#                 "session_id": "static-superadmin-session",
#                 "sms_sent": True,
#                 "otp": STATIC_SUPERADMIN_OTP
#             }, status=status.HTTP_200_OK)

#         # Ensure user exists for login
#         if purpose == 'login' and not User.objects.filter(phone_number=phone).exists():
#             return Response(
#                 {"detail": "Phone number not registered. Please register first."},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         # Rate limit
#         allowed = increment_rate_limit(phone, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX)
#         if not allowed:
#             return Response(
#                 {"detail": "Too many OTP requests for this phone. Try again later."},
#                 status=status.HTTP_429_TOO_MANY_REQUESTS,
#             )

#         # Create OTP
#         session_id, otp = create_otp_session(phone, purpose=purpose)
#         message = f"Your OTP is: {otp} (valid {OTP_TTL_MINUTES} minutes)"
#         sms_ok = send_sms_via_provider(phone, message)

#         resp = {"message": "OTP sent", "session_id": session_id, "sms_sent": sms_ok}
#         if getattr(settings, 'SMS_BACKEND', 'console') == 'console':
#             resp['otp'] = otp
#         return Response(resp, status=status.HTTP_200_OK)


# # ---------------------- VERIFY OTP ----------------------
# class VerifyOTPView(APIView):
#     """
#     Verify OTP by session_id + otp.
#     For register → activate user & send Kafka event.
#     For login → return JWT tokens.
#     """
#     def post(self, request):
#         serializer = VerifyOTPSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         session_id = serializer.validated_data['session_id']
#         provided_otp = serializer.validated_data['otp']

#         # --- SuperAdmin OTP ---
#         if session_id == "static-superadmin-session":
#             if provided_otp == STATIC_SUPERADMIN_OTP:
#                 try:
#                     user = User.objects.get(phone_number=STATIC_SUPERADMIN_PHONE)
#                 except User.DoesNotExist:
#                     return Response(
#                         {"detail": "Super Admin not found in DB. Create manually."},
#                         status=status.HTTP_404_NOT_FOUND,
#                     )
#                 tokens = get_tokens_for_user(user, request=request)
#                 return Response({
#                     "message": "Super Admin login successful.",
#                     "tokens": tokens,
#                     "user": {
#                         "user_id": str(user.id),
#                         "phone_number": user.phone_number,
#                         "full_name": user.full_name,
#                         "email": user.email,
#                         "role": user.role.name if user.role else None,
#                     },
#                 }, status=status.HTTP_200_OK)
#             return Response({"detail": "Invalid OTP for super admin."}, status=status.HTTP_400_BAD_REQUEST)

#         # --- Normal User OTP ---
#         session = get_otp_session(session_id)
#         if not session:
#             return Response(
#                 {"detail": "Invalid or expired session. Request new OTP."},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         phone = session.get('phone_number')
#         purpose = session.get('purpose')
#         attempts = session.get('attempts', 0)

#         if attempts >= 5:
#             delete_otp_session(session_id)
#             return Response(
#                 {"detail": "Too many attempts. Request a new OTP."},
#                 status=status.HTTP_429_TOO_MANY_REQUESTS,
#             )

#         if session.get('otp') != provided_otp:
#             increment_session_attempts(session_id)
#             return Response({"detail": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

#         # ✅ OTP valid
#         delete_otp_session(session_id)

#         # --- Registration ---
#         if purpose == 'register':
#             try:
#                 user = User.objects.get(phone_number=phone)
#                 user.is_active = True
#                 if hasattr(user, 'is_verified'):
#                     user.is_verified = True
#                 user.save(update_fields=['is_active'])

#                 # Kafka event
#                 user_data = {
#                     "auth_user_id": str(user.id),
#                     "phone_number": user.phone_number,
#                     "email": user.email,
#                     "full_name": user.full_name,
#                     "role": user.role.name if user.role else None,
#                     "permissions": [p.codename for p in user.role.permissions.all()] if user.role else [],
#                 }
#                 publish_user_event("USER_VERIFIED", user_data)

#                 return Response(
#                     {"message": "Phone verified. You can now login."},
#                     status=status.HTTP_200_OK,
#                 )
#             except User.DoesNotExist:
#                 return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

#         # --- Login ---
#         if purpose == 'login':
#             try:
#                 user = User.objects.get(phone_number=phone)
#             except User.DoesNotExist:
#                 return Response({"detail": "Phone number not registered."}, status=status.HTTP_404_NOT_FOUND)

#             tokens = get_tokens_for_user(user, request=request)
#             return Response({
#                 "message": "OTP verified. Login successful.",
#                 "tokens": tokens,
#                 "user": {
#                     "user_id": str(user.id),
#                     "phone_number": user.phone_number,
#                     "full_name": user.full_name,
#                     "role": user.role.name if user.role else None,
#                     "permissions": [p.codename for p in user.role.permissions.all()] if user.role else [],
#                 },
#             }, status=status.HTTP_200_OK)

#         return Response({"message": "OTP verified."}, status=status.HTTP_200_OK)


# # ---------------------- REFRESH TOKEN ----------------------
# class RefreshTokenView(APIView):
#     """
#     Accept opaque refresh token, rotate and return new access + refresh.
#     """
#     def post(self, request):
#         token = request.data.get('refresh')
#         if not token:
#             return Response({"detail": "Refresh token required."}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             user, access, new_refresh = verify_and_rotate_refresh_token(token, request=request)
#         except ValueError as e:
#             return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

#         return Response({"access": access, "refresh": new_refresh}, status=status.HTTP_200_OK)


# # ---------------------- LOGOUT ----------------------
# class LogoutView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request):
#         refresh_plain = request.data.get('refresh')

#         # Revoke one refresh token
#         if refresh_plain:
#             from .tokens import _hash_token
#             token_hash = _hash_token(refresh_plain)
#             StoredRefreshToken.objects.filter(token_hash=token_hash).update(revoked=True)

#         # Optionally revoke all
#         if request.data.get('revoke_all'):
#             StoredRefreshToken.objects.filter(user=request.user).update(revoked=True)

#         # Increment token_version to invalidate JWTs
#         request.user.token_version = (request.user.token_version or 0) + 1
#         request.user.save(update_fields=['token_version'])

#         return Response({"message": "Logged out. Tokens revoked."}, status=status.HTTP_200_OK)







# @api_view(["POST"])
# def register_superadmin(request):
#     try:
#         data = request.data
#         email = data.get("email")
#         contact = data.get("contact")
#         first_name = data.get("first_name", "")
#         last_name = data.get("last_name", "")

#         # Check if exists
#         if User.objects.filter(email=email).exists():
#             return Response({"message": "SuperAdmin already exists"}, status=status.HTTP_200_OK)

#         # Create SuperAdmin role if not exists
#         role, _ = Role.objects.get_or_create(name="SuperAdmin")

#         # Create user
#         user = User.objects.create(
#             id=uuid.uuid4(),
#             email=email,
#             contact=contact,
#             first_name=first_name,
#             last_name=last_name,
#             role=role,
#             is_active=True,
#             is_super_admin=True,
#         )

#         return Response({"message": "SuperAdmin created", "user_id": str(user.id)}, status=status.HTTP_201_CREATED)
#     except Exception as e:
#         return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# import logging
# from datetime import timedelta
# import uuid

# from django.utils import timezone
# from django.conf import settings
# from django.contrib.auth import get_user_model

# from rest_framework import status, permissions
# from rest_framework.response import Response
# from rest_framework.views import APIView
# from rest_framework.decorators import api_view

# from .kafka_producer import publish_event
# from .models import User, Role, OTP, StoredRefreshToken
# from .serializers import RegisterSerializer, SendOTPSerializer, VerifyOTPSerializer
# from .utils import (
#     create_otp_session,
#     get_otp_session,
#     increment_session_attempts,
#     delete_otp_session,
#     send_sms_via_provider,
#     increment_rate_limit,
# )
# from .tokens import get_tokens_for_user, verify_and_rotate_refresh_token

# User = get_user_model()
# logger = logging.getLogger(__name__)

# # Settings constants
# OTP_TTL_MINUTES = int(getattr(settings, 'OTP_TTL_SECONDS', 600)) // 60
# RATE_LIMIT_WINDOW = getattr(settings, 'OTP_RATE_LIMIT_WINDOW_SECONDS', 3600)
# RATE_LIMIT_MAX = getattr(settings, 'OTP_RATE_LIMIT_MAX_PER_WINDOW', 5)
# STATIC_SUPERADMIN_PHONE = getattr(settings, 'STATIC_SUPERADMIN_PHONE', None)
# STATIC_SUPERADMIN_OTP = getattr(settings, 'STATIC_SUPERADMIN_OTP', None)


# # ---------------------- REGISTER ----------------------
# class RegisterView(APIView):
#     """Register user and create OTP session (returns session_id)."""
#     def post(self, request):
#         serializer = RegisterSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.save()

#         phone = user.phone_number

#         # Rate limit
#         allowed = increment_rate_limit(phone, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX)
#         if not allowed:
#             return Response(
#                 {"detail": "Too many OTP requests for this phone. Try again later."},
#                 status=status.HTTP_429_TOO_MANY_REQUESTS,
#             )

#         # Create OTP
#         session_id, otp = create_otp_session(phone, purpose='register')
#         message = f"Your registration OTP is: {otp} (valid {OTP_TTL_MINUTES} minutes)"
#         sms_ok = send_sms_via_provider(phone, message)

#         # ✅ Kafka Event — send "USER_CREATED"
#         payload = {
#             "auth_user_id": str(user.id),
#             "phone_number": phone,
#             "email": user.email,
#             "full_name": user.full_name,
#             "role": user.role.name if user.role else None,
#         }
#         publish_event("USER_CREATED", payload)

#         # Response
#         response = {
#             "message": "User registered. OTP sent for verification.",
#             "session_id": session_id,
#             "sms_sent": sms_ok,
#         }
#         if getattr(settings, 'SMS_BACKEND', 'console') == 'console':
#             response['otp'] = otp  # only in dev

#         return Response(response, status=status.HTTP_201_CREATED)


# # ---------------------- SEND OTP ----------------------
# class SendOTPView(APIView):
#     """Request OTP for login (returns session_id)."""
#     def post(self, request):
#         serializer = SendOTPSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         phone = serializer.validated_data['phone_number']
#         purpose = serializer.validated_data.get('purpose', 'login')

#         # Static SuperAdmin OTP (for dev/test)
#         if STATIC_SUPERADMIN_PHONE and phone == STATIC_SUPERADMIN_PHONE and purpose == 'login':
#             return Response({
#                 "message": "Static OTP for super admin (dev).",
#                 "session_id": "static-superadmin-session",
#                 "sms_sent": True,
#                 "otp": STATIC_SUPERADMIN_OTP
#             }, status=status.HTTP_200_OK)

#         # Ensure user exists for login
#         if purpose == 'login' and not User.objects.filter(phone_number=phone).exists():
#             return Response(
#                 {"detail": "Phone number not registered. Please register first."},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         # Rate limit
#         allowed = increment_rate_limit(phone, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX)
#         if not allowed:
#             return Response(
#                 {"detail": "Too many OTP requests for this phone. Try again later."},
#                 status=status.HTTP_429_TOO_MANY_REQUESTS,
#             )

#         # Create OTP
#         session_id, otp = create_otp_session(phone, purpose=purpose)
#         message = f"Your OTP is: {otp} (valid {OTP_TTL_MINUTES} minutes)"
#         sms_ok = send_sms_via_provider(phone, message)

#         resp = {"message": "OTP sent", "session_id": session_id, "sms_sent": sms_ok}
#         if getattr(settings, 'SMS_BACKEND', 'console') == 'console':
#             resp['otp'] = otp
#         return Response(resp, status=status.HTTP_200_OK)


# # ---------------------- VERIFY OTP ----------------------
# class VerifyOTPView(APIView):
#     """Verify OTP for register or login."""
#     def post(self, request):
#         serializer = VerifyOTPSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         session_id = serializer.validated_data['session_id']
#         provided_otp = serializer.validated_data['otp']

#         # --- SuperAdmin OTP ---
#         if session_id == "static-superadmin-session":
#             if provided_otp == STATIC_SUPERADMIN_OTP:
#                 try:
#                     user = User.objects.get(phone_number=STATIC_SUPERADMIN_PHONE)
#                 except User.DoesNotExist:
#                     return Response(
#                         {"detail": "Super Admin not found in DB. Create manually."},
#                         status=status.HTTP_404_NOT_FOUND,
#                     )
#                 tokens = get_tokens_for_user(user, request=request)
#                 return Response({
#                     "message": "Super Admin login successful.",
#                     "tokens": tokens,
#                     "user": {
#                         "user_id": str(user.id),
#                         "phone_number": user.phone_number,
#                         "full_name": user.full_name,
#                         "email": user.email,
#                         "role": user.role.name if user.role else None,
#                     },
#                 }, status=status.HTTP_200_OK)
#             return Response({"detail": "Invalid OTP for super admin."}, status=status.HTTP_400_BAD_REQUEST)

#         # --- Normal User OTP ---
#         session = get_otp_session(session_id)
#         if not session:
#             return Response(
#                 {"detail": "Invalid or expired session. Request new OTP."},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         phone = session.get('phone_number')
#         purpose = session.get('purpose')
#         attempts = session.get('attempts', 0)

#         if attempts >= 5:
#             delete_otp_session(session_id)
#             return Response(
#                 {"detail": "Too many attempts. Request a new OTP."},
#                 status=status.HTTP_429_TOO_MANY_REQUESTS,
#             )

#         if session.get('otp') != provided_otp:
#             increment_session_attempts(session_id)
#             return Response({"detail": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

#         # ✅ OTP valid
#         delete_otp_session(session_id)

#         # --- Registration ---
#         if purpose == 'register':
#             try:
#                 user = User.objects.get(phone_number=phone)
#                 user.is_active = True
#                 if hasattr(user, 'is_verified'):
#                     user.is_verified = True
#                 user.save(update_fields=['is_active', 'is_verified'])

#                 # ✅ Kafka Event — send "USER_VERIFIED"
#                 user_data = {
#                     "auth_user_id": str(user.id),
#                     "phone_number": user.phone_number,
#                     "email": user.email,
#                     "full_name": user.full_name,
#                     "role": user.role.name if user.role else None,
#                     "permissions": [p.codename for p in user.role.permissions.all()] if user.role else [],
#                 }
#                 publish_event("USER_VERIFIED", user_data)

#                 return Response(
#                     {"message": "Phone verified. You can now login."},
#                     status=status.HTTP_200_OK,
#                 )
#             except User.DoesNotExist:
#                 return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

#         # --- Login ---
#         if purpose == 'login':
#             try:
#                 user = User.objects.get(phone_number=phone)
#             except User.DoesNotExist:
#                 return Response({"detail": "Phone number not registered."}, status=status.HTTP_404_NOT_FOUND)

#             tokens = get_tokens_for_user(user, request=request)
#             return Response({
#                 "message": "OTP verified. Login successful.",
#                 "tokens": tokens,
#                 "user": {
#                     "user_id": str(user.id),
#                     "phone_number": user.phone_number,
#                     "full_name": user.full_name,
#                     "role": user.role.name if user.role else None,
#                     "permissions": [p.codename for p in user.role.permissions.all()] if user.role else [],
#                 },
#             }, status=status.HTTP_200_OK)

#         return Response({"message": "OTP verified."}, status=status.HTTP_200_OK)


# # ---------------------- REFRESH TOKEN ----------------------
# class RefreshTokenView(APIView):
#     """Accept opaque refresh token, rotate and return new access + refresh."""
#     def post(self, request):
#         token = request.data.get('refresh')
#         if not token:
#             return Response({"detail": "Refresh token required."}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             user, access, new_refresh = verify_and_rotate_refresh_token(token, request=request)
#         except ValueError as e:
#             return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

#         return Response({"access": access, "refresh": new_refresh}, status=status.HTTP_200_OK)


# # ---------------------- LOGOUT ----------------------
# class LogoutView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request):
#         refresh_plain = request.data.get('refresh')

#         # Revoke one refresh token
#         if refresh_plain:
#             from .tokens import _hash_token
#             token_hash = _hash_token(refresh_plain)
#             StoredRefreshToken.objects.filter(token_hash=token_hash).update(revoked=True)

#         # Optionally revoke all
#         if request.data.get('revoke_all'):
#             StoredRefreshToken.objects.filter(user=request.user).update(revoked=True)

#         # Increment token_version to invalidate JWTs
#         request.user.token_version = (request.user.token_version or 0) + 1
#         request.user.save(update_fields=['token_version'])

#         return Response({"message": "Logged out. Tokens revoked."}, status=status.HTTP_200_OK)


# # ---------------------- REGISTER SUPERADMIN ----------------------
# @api_view(["POST"])
# def register_superadmin(request):
#     """Create SuperAdmin (only once)."""
#     try:
#         data = request.data
#         email = data.get("email")
#         contact = data.get("contact")
#         first_name = data.get("first_name", "")
#         last_name = data.get("last_name", "")

#         # Check if exists
#         if User.objects.filter(email=email).exists():
#             return Response({"message": "SuperAdmin already exists"}, status=status.HTTP_200_OK)

#         # Create SuperAdmin role if not exists
#         role, _ = Role.objects.get_or_create(name="SuperAdmin")

#         # Create user
#         user = User.objects.create(
#             id=uuid.uuid4(),
#             email=email,
#             contact=contact,
#             first_name=first_name,
#             last_name=last_name,
#             role=role,
#             is_active=True,
#             is_super_admin=True,
#         )

#         # ✅ Kafka Event — SuperAdmin created
#         publish_event("SUPERADMIN_CREATED", {
#             "auth_user_id": str(user.id),
#             "email": user.email,
#             "contact": user.contact,
#             "role": "SuperAdmin",
#         })

#         return Response({"message": "SuperAdmin created", "user_id": str(user.id)}, status=status.HTTP_201_CREATED)
#     except Exception as e:
#         logger.exception("Failed to register superadmin.")
#         return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



import logging
import uuid
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework import viewsets
from .serializers import RoleSerializer, PermissionSerializer
from rest_framework.decorators import api_view, permission_classes
from .models import Permission, Role
from .serializers import PermissionSerializer, RoleSerializer
from .kafka_producer import publish_event
from .models import User, Role, OTP, StoredRefreshToken
from .serializers import RegisterSerializer, SendOTPSerializer, VerifyOTPSerializer,UserUpdateSerializer
from .utils import (
    create_otp_session,
    get_otp_session,
    increment_session_attempts,
    delete_otp_session,
    send_sms_via_provider,
    increment_rate_limit,
)
from .tokens import get_tokens_for_user, verify_and_rotate_refresh_token
from .kafka_producer import publish_event

logger = logging.getLogger(__name__)
User = get_user_model()

# Settings constants
OTP_TTL_MINUTES = int(getattr(settings, 'OTP_TTL_SECONDS', 600)) // 60
RATE_LIMIT_WINDOW = getattr(settings, 'OTP_RATE_LIMIT_WINDOW_SECONDS', 3600)
RATE_LIMIT_MAX = getattr(settings, 'OTP_RATE_LIMIT_MAX_PER_WINDOW', 5)
STATIC_SUPERADMIN_PHONE = getattr(settings, 'STATIC_SUPERADMIN_PHONE', None)
STATIC_SUPERADMIN_OTP = getattr(settings, 'STATIC_SUPERADMIN_OTP', None)


# # ---------------------- REGISTER ----------------------
# class RegisterView(APIView):
#     """Register user and create OTP session (returns session_id)."""
#     permission_classes = [AllowAny]
#     def post(self, request):
#         serializer = RegisterSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.save()

#         phone = user.phone_number

#         # Rate limit check
#         if not increment_rate_limit(phone, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX):
#             return Response(
#                 {"detail": "Too many OTP requests for this phone. Try again later."},
#                 status=status.HTTP_429_TOO_MANY_REQUESTS,
#             )

#         # Create OTP session
#         session_id, otp = create_otp_session(phone, purpose='register')
#         message = f"Your registration OTP is: {otp} (valid {OTP_TTL_MINUTES} minutes)"
#         sms_ok = send_sms_via_provider(phone, message)

#         # ✅ Kafka Event — send "USER_CREATED"
#         try:
#             payload = {
#                 "auth_user_id": str(user.id),
#                 "phone_number": phone,
#                 "email": user.email,
#                 "full_name": user.full_name,
#                 "role": user.role.name if user.role else None,
#             }
#             publish_event("USER_CREATED", payload)
#         except Exception as e:
#             logger.error(f"Kafka USER_CREATED publish failed: {e}")

#         response = {
#             "message": "User registered. OTP sent for verification.",
#             "session_id": session_id,
#             "sms_sent": sms_ok,
#         }
#         if getattr(settings, 'SMS_BACKEND', 'console') == 'console':
#             response['otp'] = otp  # only in dev

#         return Response(response, status=status.HTTP_201_CREATED)

class RegisterView(APIView):
    """Register user and create OTP session (returns session_id)."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        phone = user.phone_number

        # Rate limit
        if not increment_rate_limit(phone, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX):
            return Response(
                {"detail": "Too many OTP requests for this phone. Try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Create OTP session
        session_id, otp = create_otp_session(phone, purpose='register')
        message = f"Your registration OTP is: {otp} (valid {OTP_TTL_MINUTES} minutes)"
        sms_ok = send_sms_via_provider(phone, message)

        # ⭐ Kafka Event — send user role name (NOT ID)
        try:
            payload = {
                "auth_user_id": str(user.id),
                "phone_number": phone,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.name.lower() if user.role else None,
            }
            publish_event("USER_CREATED", payload)
        except Exception as e:
            logger.error(f"Kafka USER_CREATED publish failed: {e}")

        response = {
            "message": "User registered. OTP sent for verification.",
            "session_id": session_id,
            "sms_sent": sms_ok,
        }

        if getattr(settings, 'SMS_BACKEND', 'console') == 'console':
            response['otp'] = otp

        return Response(response, status=status.HTTP_201_CREATED)


class SendOTPView(APIView):
    """Request OTP for login or registration (returns session_id)."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone_number']
        purpose = serializer.validated_data.get('purpose', 'login')

        # ---------------------- SUPER ADMIN STATIC OTP ----------------------
        if STATIC_SUPERADMIN_PHONE and phone == STATIC_SUPERADMIN_PHONE and purpose == 'login':
            return Response({
                "message": "Static OTP for super admin (dev mode).",
                "session_id": "static-superadmin-session",
                "sms_sent": True,
                "otp": STATIC_SUPERADMIN_OTP
            }, status=status.HTTP_200_OK)

        # ---------------------- LOGIN OTP ----------------------
        if purpose == "login":
            try:
                user = User.objects.get(phone_number=phone)

                # ⭐ If user is NOT verified → do NOT block
                # We will verify + login using ONE OTP
                if not user.is_active:
                    purpose = "auto_verify_login"  # ⭐ Important change

            except User.DoesNotExist:
                return Response(
                    {"detail": "Phone number not registered. Please register first."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # ---------------------- RATE LIMIT ----------------------
        if not increment_rate_limit(phone, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX):
            return Response(
                {"detail": "Too many OTP requests. Try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # ---------------------- GENERATE OTP ----------------------
        session_id, otp = create_otp_session(phone, purpose=purpose)
        message = f"Your OTP is: {otp} (valid {OTP_TTL_MINUTES} minutes)"
        sms_ok = send_sms_via_provider(phone, message)

        response = {
            "message": "OTP sent successfully.",
            "session_id": session_id,
            "sms_sent": sms_ok
        }

        if getattr(settings, 'SMS_BACKEND', 'console') == 'console':
            response['otp'] = otp  # For development only

        return Response(response, status=status.HTTP_200_OK)

def transform_for_frontend(tokens, user):
    """Transform backend user and tokens into frontend-expected structure."""
    return {
        "userAbilityRules": [{"action": "manage", "subject": "all"}],
        "accessToken": tokens.get("access"),
        "userData": {
            "id": str(user.id),
            "fullName": user.full_name,
            "username": user.full_name,
            "avatar": "/images/avatars/avatar-1.png",
            "email": user.email or f"{user.phone_number}@demo.com",
            "role": user.role.name if user.role else None,
        },
    }


from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

# class VerifyOTPView(APIView):
#     """Verify OTP for register, login, or auto_verify_login."""
#     permission_classes = [AllowAny]

#     def post(self, request):
#         serializer = VerifyOTPSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         session_id = serializer.validated_data["session_id"]
#         provided_otp = serializer.validated_data["otp"]
#         remember_me = request.data.get("remember_me", False)

#         # ---------------- SUPERADMIN STATIC OTP ----------------
#         if session_id == "static-superadmin-session":
#             if provided_otp == STATIC_SUPERADMIN_OTP:
#                 user = User.objects.get(phone_number=STATIC_SUPERADMIN_PHONE)
#                 tokens = get_tokens_for_user(user, request=request, remember_me=remember_me)

#                 res = transform_for_frontend(tokens, user)
#                 res["message"] = "Super Admin login successful."
#                 res["remember_me"] = remember_me
#                 return Response(res, status=status.HTTP_200_OK)

#             return Response({"detail": "Invalid OTP for super admin"}, status=status.HTTP_400_BAD_REQUEST)

#         # ---------------- NORMAL OTP ----------------
#         session = get_otp_session(session_id)
#         if not session:
#             return Response({"detail": "Invalid or expired session. Request new OTP."},
#                             status=status.HTTP_400_BAD_REQUEST)

#         phone = session["phone_number"]
#         purpose = session["purpose"]
#         attempts = session.get("attempts", 0)

#         if attempts >= 5:
#             delete_otp_session(session_id)
#             return Response({"detail": "Too many attempts. Try again later."},
#                             status=status.HTTP_429_TOO_MANY_REQUESTS)

#         if session["otp"] != provided_otp:
#             increment_session_attempts(session_id)
#             return Response({"detail": "Invalid OTP."},
#                             status=status.HTTP_400_BAD_REQUEST)

#         # OTP is valid → delete session
#         delete_otp_session(session_id)

#         # ======================================================
#         # ⭐ CASE 1: Registration
#         # ======================================================
#         if purpose == "register":
#             return self.handle_registration_verify(phone)

#         # ======================================================
#         # ⭐ CASE 2: Normal Login
#         # ======================================================
#         if purpose == "login":
#             return self.handle_login(phone, request, remember_me)

#         # ======================================================
#         # ⭐ CASE 3: Auto Verify + Login (single OTP)
#         # ======================================================
#         if purpose == "auto_verify_login":
#             return self.handle_auto_verify_login(phone, request, remember_me)

#         return Response({"message": "OTP verified."}, status=status.HTTP_200_OK)

#     # ----------------------------------------------------------------------
#     # HELPERS
#     # ----------------------------------------------------------------------

#     def handle_registration_verify(self, phone):
#         try:
#             user = User.objects.get(phone_number=phone)
#         except User.DoesNotExist:
#             return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

#         # Activate user
#         user.is_active = True
#         if hasattr(user, "is_verified"):
#             user.is_verified = True
#         user.save(update_fields=["is_active", "is_verified"] if hasattr(user, "is_verified") else ["is_active"])

#         # Publish Kafka event
#         try:
#             user_data = {
#                 "auth_user_id": str(user.id),
#                 "phone_number": user.phone_number,
#                 "email": user.email,
#                 "full_name": user.full_name,
#                 "role": user.role.name if user.role else None,
#                 "permissions": [p.codename for p in user.role.permissions.all()] if user.role else [],
#             }
#             publish_event("USER_VERIFIED", user_data, role=user_data.get("role"))
#         except Exception as e:
#             logger.error(f"Kafka USER_VERIFIED failed: {e}")

#         return Response({"message": "Phone verified. You can now login."}, status=status.HTTP_200_OK)

#     def handle_login(self, phone, request, remember_me):
#         try:
#             user = User.objects.get(phone_number=phone)
#         except User.DoesNotExist:
#             return Response({"detail": "Phone not registered."}, status=status.HTTP_404_NOT_FOUND)

#         tokens = get_tokens_for_user(user, request=request, remember_me=remember_me)

#         res = transform_for_frontend(tokens, user)
#         res["message"] = "OTP verified. Login successful."
#         res["remember_me"] = remember_me
#         return Response(res, status=status.HTTP_200_OK)

#     def handle_auto_verify_login(self, phone, request, remember_me):
#         """
#         ⭐ One OTP → Verify the user (if not active) + Login immediately
#         """
#         try:
#             user = User.objects.get(phone_number=phone)
#         except User.DoesNotExist:
#             return Response({"detail": "Phone not registered."}, status=status.HTTP_404_NOT_FOUND)

#         # STEP 1 → Verify user if needed
#         if not user.is_active:
#             user.is_active = True
#             if hasattr(user, "is_verified"):
#                 user.is_verified = True

#             user.save(update_fields=["is_active", "is_verified"] if hasattr(user, "is_verified") else ["is_active"])

#             # Kafka event for verification
#             try:
#                 user_data = {
#                     "auth_user_id": str(user.id),
#                     "phone_number": user.phone_number,
#                     "email": user.email,
#                     "full_name": user.full_name,
#                     "role": user.role.name if user.role else None,
#                 }
#                 publish_event("USER_VERIFIED", user_data)
#             except Exception as e:
#                 logger.error(f"Kafka USER_VERIFIED failed: {e}")

#         # STEP 2 → Login immediately
#         tokens = get_tokens_for_user(user, request=request, remember_me=remember_me)

#         res = transform_for_frontend(tokens, user)
#         res["message"] = "OTP verified. Account verified and logged in."
#         res["remember_me"] = remember_me
#         return Response(res, status=status.HTTP_200_OK)





class VerifyOTPView(APIView):
    """Verify OTP for register, login, or auto_verify_login."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_id = serializer.validated_data["session_id"]
        provided_otp = serializer.validated_data["otp"]
        remember_me = request.data.get("remember_me", False)

        # ---------- SUPERADMIN STATIC OTP ----------
        if session_id == "static-superadmin-session":
            if provided_otp == STATIC_SUPERADMIN_OTP:
                user = User.objects.get(phone_number=STATIC_SUPERADMIN_PHONE)
                tokens = get_tokens_for_user(user, request=request, remember_me=remember_me)

                res = transform_for_frontend(tokens, user)
                res["message"] = "Super Admin login successful."
                res["remember_me"] = remember_me
                return Response(res, status=status.HTTP_200_OK)

            return Response({"detail": "Invalid OTP for super admin"}, status=status.HTTP_400_BAD_REQUEST)

        # ---------- NORMAL OTP ----------
        session = get_otp_session(session_id)
        if not session:
            return Response({"detail": "Invalid or expired session. Request new OTP."},
                            status=status.HTTP_400_BAD_REQUEST)

        phone = session["phone_number"]
        purpose = session["purpose"]
        attempts = session.get("attempts", 0)

        if attempts >= 5:
            delete_otp_session(session_id)
            return Response({"detail": "Too many attempts. Try again later."},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        if session["otp"] != provided_otp:
            increment_session_attempts(session_id)
            return Response({"detail": "Invalid OTP."},
                            status=status.HTTP_400_BAD_REQUEST)

        # OTP valid → delete session
        delete_otp_session(session_id)

        # ---------- CASE 1: Registration ----------
        if purpose == "register":
            return self.handle_registration_verify(phone)

        # ---------- CASE 2: Normal Login ----------
        if purpose == "login":
            return self.handle_login(phone, request, remember_me)

        # ---------- CASE 3: Auto Verify + Login ----------
        if purpose == "auto_verify_login":
            return self.handle_auto_verify_login(phone, request, remember_me)

        return Response({"message": "OTP verified."}, status=status.HTTP_200_OK)

    # ================================================================
    # HELPERS
    # ================================================================

    def handle_registration_verify(self, phone):
        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Activate user
        user.is_active = True
        if hasattr(user, "is_verified"):
            user.is_verified = True
        user.save()

        # ⭐ Send ONLY role name
        try:
            user_data = {
                "auth_user_id": str(user.id),
                "phone_number": user.phone_number,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.name.lower() if user.role else None,
                "permissions": [
                    p.codename for p in user.role.permissions.all()
                ] if user.role else [],
            }

            publish_event("USER_VERIFIED", user_data)   # ⭐ FIXED — no role= argument
        except Exception as e:
            logger.error(f"Kafka USER_VERIFIED failed: {e}")

        return Response({"message": "Phone verified. You can now login."}, status=status.HTTP_200_OK)

    def handle_login(self, phone, request, remember_me):
        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            return Response({"detail": "Phone not registered."}, status=status.HTTP_404_NOT_FOUND)

        tokens = get_tokens_for_user(user, request=request, remember_me=remember_me)

        res = transform_for_frontend(tokens, user)
        res["message"] = "OTP verified. Login successful."
        res["remember_me"] = remember_me
        return Response(res, status=status.HTTP_200_OK)

    def handle_auto_verify_login(self, phone, request, remember_me):
        """Verify + Login using single OTP."""
        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            return Response({"detail": "Phone not registered."}, status=status.HTTP_404_NOT_FOUND)

        # Verify if needed
        if not user.is_active:
            user.is_active = True
            if hasattr(user, "is_verified"):
                user.is_verified = True
            user.save()

            try:
                user_data = {
                    "auth_user_id": str(user.id),
                    "phone_number": user.phone_number,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role.name.lower() if user.role else None,
                }
                publish_event("USER_VERIFIED", user_data)
            except Exception as e:
                logger.error(f"Kafka USER_VERIFIED failed: {e}")

        # Login
        tokens = get_tokens_for_user(user, request=request, remember_me=remember_me)

        res = transform_for_frontend(tokens, user)
        res["message"] = "OTP verified. Account verified and logged in."
        res["remember_me"] = remember_me
        return Response(res, status=status.HTTP_200_OK)



# ---------------------- REFRESH TOKEN ----------------------
class RefreshTokenView(APIView):
    """Accept opaque refresh token, rotate and return new access + refresh."""
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('refresh')
        if not token:
            return Response({"detail": "Refresh token required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user, access, new_refresh = verify_and_rotate_refresh_token(token, request=request)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"access": access, "refresh": new_refresh}, status=status.HTTP_200_OK)


# ---------------------- LOGOUT ----------------------
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_plain = request.data.get('refresh')

        # Revoke one refresh token
        if refresh_plain:
            from .tokens import _hash_token
            token_hash = _hash_token(refresh_plain)
            StoredRefreshToken.objects.filter(token_hash=token_hash).update(revoked=True)

        # Optionally revoke all
        if request.data.get('revoke_all'):
            StoredRefreshToken.objects.filter(user=request.user).update(revoked=True)

        # Increment token_version to invalidate JWTs
        request.user.token_version = (request.user.token_version or 0) + 1
        request.user.save(update_fields=['token_version'])

        return Response({"message": "Logged out. Tokens revoked."}, status=status.HTTP_200_OK)

# ---------------------- REGISTER USER (ADMIN + SERVICE PROVIDER) ----------------------
@api_view(["POST"])
def register_superadmin(request):
    """
    Unified API to register:
      - Admin (created by SuperAdmin)
      - Service Provider (self-registration)
    """
    try:
        data = request.data
        email = data.get("email")
        contact = data.get("contact")
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        user_type = data.get("user_type", "").lower()  # "admin" or "service_provider"
        provider_type = data.get("provider_type", "organization")  # org / individual

        if not email or not contact or not user_type:
            return Response(
                {"error": "Missing required fields: email, contact, or user_type"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 🔍 Prevent duplicate user
        # if User.objects.filter(email=email).exists():
        #     return Response(
        #         {"message": "User already exists"},
        #         status=status.HTTP_200_OK
        #     )
        existing_user = User.objects.filter(phone_number=phone).first()
        if existing_user and not existing_user.is_active:
            # Resend OTP automatically
            session_id, otp = create_otp_session(phone, purpose='register')
            message = f"Your OTP is: {otp} (valid {OTP_TTL_MINUTES} minutes)"
            send_sms_via_provider(phone, message)
            return Response({
                "message": "User already exists but not verified. OTP resent.",
                "session_id": session_id,
                "otp": otp  # only for dev
            }, status=status.HTTP_200_OK)

        # ---------------------- ADMIN REGISTRATION (BY SUPERADMIN) ----------------------
        if user_type == "admin":
            # 🧩 Ensure only SuperAdmin can create Admins
            created_by = request.headers.get("Created-By")
            if not created_by:
                return Response(
                    {"error": "Missing 'Created-By' header (SuperAdmin ID required)."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            try:
                super_admin = User.objects.get(id=created_by, is_super_admin=True)
            except User.DoesNotExist:
                return Response(
                    {"error": "Only SuperAdmin can create Admin users."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # 🧩 Create Role
            role, _ = Role.objects.get_or_create(name="Admin")

            user = User.objects.create(
                id=uuid.uuid4(),
                email=email,
                contact=contact,
                first_name=first_name,
                last_name=last_name,
                role=role,
                is_active=True,
                is_super_admin=False,
            )

            event_data = {
                "auth_user_id": str(user.id),
                "email": user.email,
                "contact": user.contact,
                "role": "admin",
                "created_by": str(super_admin.id),
            }

            try:
                publish_event("ADMIN_CREATED", event_data, role="admin")
                logger.info(f"✅ ADMIN_CREATED event published for {user.email}")
            except Exception as e:
                logger.error(f"❌ Kafka ADMIN_CREATED publish failed: {e}")

            return Response(
                {"message": "Admin created successfully", "user_id": str(user.id)},
                status=status.HTTP_201_CREATED,
            )

        # ---------------------- SERVICE PROVIDER REGISTRATION ----------------------
        elif user_type == "service_provider":
            role, _ = Role.objects.get_or_create(name="ServiceProvider")

            user = User.objects.create(
                id=uuid.uuid4(),
                email=email,
                contact=contact,
                first_name=first_name,
                last_name=last_name,
                role=role,
                is_active=True,
            )

            event_data = {
                "auth_user_id": str(user.id),
                "email": user.email,
                "contact": user.contact,
                "full_name": f"{user.first_name} {user.last_name}".strip(),
                "role": "organization" if provider_type == "organization" else "individual",
                "permissions": [],
            }

            try:
                publish_event("USER_CREATED", event_data, role=provider_type)
                logger.info(f"✅ USER_CREATED event published for {user.email}")
            except Exception as e:
                logger.error(f"❌ Kafka USER_CREATED publish failed: {e}")

            return Response(
                {"message": "Service Provider registered successfully", "user_id": str(user.id)},
                status=status.HTTP_201_CREATED,
            )

        else:
            return Response(
                {"error": "Invalid user_type. Use 'admin' or 'service_provider'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    except Exception as e:
        logger.exception("❌ Failed to register user.")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



    
    
class PermissionViewSet(viewsets.ModelViewSet):
    """
    ✅ Full CRUD for Permission model
    GET /permissions/        → list
    POST /permissions/       → create
    GET /permissions/{id}/   → retrieve
    PUT /permissions/{id}/   → update
    PATCH /permissions/{id}/ → partial update
    DELETE /permissions/{id}/→ delete
    """
    queryset = Permission.objects.all().order_by("codename")
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]


class RoleViewSet(viewsets.ModelViewSet):
    """
    ✅ Full CRUD for Role model (with permission assignment)
    GET /roles/        → list all roles
    POST /roles/       → create new role
    GET /roles/{id}/   → get role details
    PUT /roles/{id}/   → update all fields
    PATCH /roles/{id}/ → partial update
    DELETE /roles/{id}/→ delete role
    """
    queryset = Role.objects.all().prefetch_related("permissions")
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        """
        Overriding update to safely handle permissions and partial updates.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def assign_permissions(self, request, pk=None):
        """
        Custom endpoint: POST /roles/{id}/assign_permissions/
        Assign or update permissions for a role.
        """
        role = get_object_or_404(Role, pk=pk)
        permission_ids = request.data.get("permissions", [])
        role.permissions.set(permission_ids)
        role.save()
        return Response(
            {"message": "Permissions updated successfully."},
            status=status.HTTP_200_OK
        )
        
        
        
@api_view(["GET"])
@permission_classes([AllowAny])
def public_roles(request):
    """
    ✅ Return only roles that can be selected during user registration
       (organization and individual).
    """
    permission_classes = [AllowAny]
    allowed_roles = ["organization", "individual"]
    roles = Role.objects.filter(name__in=allowed_roles)
    serializer = RoleSerializer(roles, many=True)
    return Response(serializer.data)

class UserViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]  # adjust for service-to-service calls (see notes)

    def retrieve(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        serializer = UserUpdateSerializer(user)
        return Response(serializer.data)

    def list(self, request):
        qs = User.objects.filter(is_active=True)
        serializer = UserUpdateSerializer(qs, many=True)
        return Response(serializer.data)

    
    def partial_update(self, request, pk=None):
        """Handles PATCH requests and publishes USER_UPDATED to Kafka"""
        user = get_object_or_404(User, pk=pk)
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # ✅ Refresh from DB to get latest role relation
        user.refresh_from_db()

        # Resolve dynamic role safely
        dynamic_role = (
            getattr(user.role, "name", None)
            or serializer.data.get("role")
            or request.data.get("role")
        )

        logger.info(f"🧩 Dynamic role resolved: {dynamic_role} for user {user.id}")

        if dynamic_role:
            publish_event(
                event_type="USER_UPDATED",
                data={
                    "auth_user_id": str(user.id),
                    "full_name": serializer.data.get("full_name") or user.full_name,
                    "email": serializer.data.get("email") or user.email,
                    "phone_number": serializer.data.get("phone_number") or user.phone_number,
                    "role": dynamic_role,
                },
            )
            logger.info(f"✅ USER_UPDATED event published for role '{dynamic_role}'")
        else:
            logger.warning("⚠️ Skipping USER_UPDATED event: no valid role found.")

        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, pk=None):
        """Alias PUT -> same as PATCH"""
        return self.partial_update(request, pk)
    def destroy(self, request, pk=None):
        # 🔹 Get and delete the user
        user = get_object_or_404(User, pk=pk)
        user_id = str(user.id)

        # ✅ Safely extract dynamic role name
        dynamic_role = user.role.name if user.role else None

        # 🔹 Publish USER_DELETED event BEFORE deleting
        if dynamic_role:
            publish_event(
                event_type="USER_DELETED",
                data={
                    "auth_user_id": user_id,
                    "role": dynamic_role,
                },
            )
            logger.info(f"✅ USER_DELETED event published for role '{dynamic_role}'")
        else:
            logger.warning("⚠️ Skipping USER_DELETED event: no valid role found.")

        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    


class ResendVerificationOTPView(APIView):
    """Resend OTP for users who registered but haven't verified yet"""
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get("phone_number")
        if not phone:
            return Response(
                {"detail": "Phone number is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found. Please register first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.is_active:
            return Response(
                {"detail": "User already verified. Please login."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not increment_rate_limit(phone, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX):
            return Response(
                {"detail": "Too many OTP requests. Try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        session_id, otp = create_otp_session(phone, purpose="register")
        message = f"Your verification OTP is: {otp} (valid {OTP_TTL_MINUTES} minutes)"
        sms_ok = send_sms_via_provider(phone, message)

        response = {
            "message": "OTP resent successfully.",
            "session_id": session_id,
            "sms_sent": sms_ok,
        }
        if getattr(settings, "SMS_BACKEND", "console") == "console":
            response["otp"] = otp

        logger.info(f"🔁 OTP resent for {phone}")
        return Response(response, status=status.HTTP_200_OK)
