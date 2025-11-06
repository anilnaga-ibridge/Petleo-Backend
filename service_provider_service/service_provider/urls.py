from django.urls import path
from .views import (
    ServiceProviderProfileView,
    BusinessDetailsView,
    DocumentUploadView,
    VerificationStatusView,
    SuperAdminVerificationView
)
from .views import (
    DocumentCategoryView,
    ProviderDocumentUploadView,
    ProviderDocumentsListView,
    DocumentVerificationUpdateView,DocumentCreateView,
)
urlpatterns = [
   path("profile/", ServiceProviderProfileView.as_view(), name="provider_profile"),
    path("business/", BusinessDetailsView.as_view(), name="business_details"),
    path("documents/", DocumentUploadView.as_view(), name="document_upload"),
    path("verification/", VerificationStatusView.as_view(), name="verification_status"),
    path("admin/verify/", SuperAdminVerificationView.as_view(), name="admin_verify_provider"),

    
    
    path("admin/verify/<uuid:auth_user_id>/", SuperAdminVerificationView.as_view(), name="admin_verify_provider"),
    
     path('document/', DocumentCreateView.as_view(), name='create_document'),
    path('documents/categories/', DocumentCategoryView.as_view(), name='document_categories'),
    path('documents/upload/', ProviderDocumentUploadView.as_view(), name='upload_document'),
    path('documents/', ProviderDocumentsListView.as_view(), name='provider_documents'),
    path('documents/verify/', DocumentVerificationUpdateView.as_view(), name='verify_document'),
    
      # Verification
    path('verification/', VerificationStatusView.as_view(), name='verification_status'),

    # Super Admin Verification
    path('admin/verify/', SuperAdminVerificationView.as_view(), name="admin_verify_provider"),
]
