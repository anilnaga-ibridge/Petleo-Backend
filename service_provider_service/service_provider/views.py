from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from .services import verify_provider_by_admin
from django.utils import timezone
# service_provider/views.py
from service_provider.serializers import ProviderDocumentSerializer

from .models import (
    ServiceProvider, 
    DocumentVerification, VerificationWorkflow, VerifiedUser,Document
)
from .serializers import (
    ServiceProviderSerializer, BusinessDetailsSerializer,
    DocumentVerificationSerializer, VerificationWorkflowSerializer,DocumentSerializer
)
from service_provider.models import (
    ProviderDocument, DocumentVerificationCategory, AutoVerificationLog
)


from .serializers import DocumentVerificationCategorySerializer


class ServiceProviderProfileView(APIView):
    """
    POST: Create or update the service provider profile, including personal info, avatar, and status.
    """

    def post(self, request):
        # Extract the auth_user_id from the request body
        auth_user_id = request.data.get('auth_user_id')
        
        # Check if auth_user_id is provided
        if not auth_user_id:
            return Response({"error": "auth_user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Try to fetch the VerifiedUser by auth_user_id
        try:
            verified_user = VerifiedUser.objects.get(auth_user_id=auth_user_id)
        except VerifiedUser.DoesNotExist:
            return Response({"error": "VerifiedUser not found for this auth_user_id"}, status=status.HTTP_404_NOT_FOUND)

        # Now, try to fetch the ServiceProvider related to this VerifiedUser
        provider, created = ServiceProvider.objects.get_or_create(verified_user=verified_user)

        # Proceed to update the profile data
        serializer = ServiceProviderSerializer(provider, data=request.data, partial=True)
        
        if serializer.is_valid():
            avatar_file = request.FILES.get('avatar')

            if avatar_file:
                provider.avatar = avatar_file
                provider.avatar_size = f"{round(avatar_file.size / 1024, 2)} KB"
                provider.save(update_fields=["avatar", "avatar_size"])

            serializer.save()

            return Response({
                "message": "Provider profile updated successfully",
                "data": ServiceProviderSerializer(provider).data
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BusinessDetailsView(APIView):
    """
    POST: Create or update the provider's business info.
    """

    def post(self, request):
        # Extract IDs from request
        auth_user_id = request.data.get('auth_user_id')
        service_provider_id = request.data.get('service_provider_id')

        if not auth_user_id or not service_provider_id:
            return Response(
                {"error": "Both 'auth_user_id' and 'service_provider_id' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch related VerifiedUser and ServiceProvider
        verified_user = get_object_or_404(VerifiedUser, auth_user_id=auth_user_id)
        service_provider = get_object_or_404(ServiceProvider, id=service_provider_id)

        # Merge data for serializer (exclude direct model instances)
        business_data = request.data.copy()
        business_data["verified_user"] = str(verified_user.auth_user_id)
        business_data["service_provider"] = str(service_provider.id)

        serializer = BusinessDetailsSerializer(data=business_data)

        if serializer.is_valid():
            serializer.save(
                verified_user=verified_user,
                service_provider=service_provider
            )
            return Response({
                "message": "✅ Business details created successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DocumentUploadView(APIView):
    """
    POST: Upload provider documents
    GET: View uploaded documents
    """

    def get(self, request, auth_user_id):
        docs = get_object_or_404(DocumentVerification, verified_user__auth_user_id=auth_user_id)
        serializer = DocumentVerificationSerializer(docs)
        return Response(serializer.data)

    def post(self, request, auth_user_id):
        # Try to fetch the provider's document record
        docs = get_object_or_404(DocumentVerification, verified_user__auth_user_id=auth_user_id)
        serializer = DocumentVerificationSerializer(docs, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Documents uploaded successfully",
                "data": serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerificationStatusView(APIView):
    """
    GET: Get current verification workflow stage
    """

    def get(self, request, auth_user_id):
        workflow = get_object_or_404(VerificationWorkflow, verified_user__auth_user_id=auth_user_id)
        serializer = VerificationWorkflowSerializer(workflow)
        return Response(serializer.data)


class SuperAdminVerificationView(APIView):
    """
    Allows a SuperAdmin to verify a service provider manually.
    POST: mark provider as verified
    """

    permission_classes = [AllowAny]

    def post(self, request, auth_user_id):
        """
        Mark provider as verified by admin.
        Body: {"verified_by": "superadmin_username"}
        """
        verified_by = request.data.get("verified_by", "system_admin")

        # Find the verified user
        verified_user = get_object_or_404(VerifiedUser, auth_user_id=auth_user_id)

        result = verify_provider_by_admin(verified_user, verified_by)

        return Response(result, status=status.HTTP_200_OK)
    



class DocumentCreateView(APIView):
    """
    Create a new document type (e.g., "Business License", "Training Certificate").
    """
    
    def post(self, request):
        """
        Handle POST request to create a new document type.
        """
        # Deserialize the incoming data using the DocumentSerializer
        serializer = DocumentSerializer(data=request.data)
        
        if serializer.is_valid():
            # Save the document if the data is valid
            document = serializer.save()
            return Response({
                "message": "Document created successfully",
                "data": DocumentSerializer(document).data
            }, status=status.HTTP_201_CREATED)
        
        # If the data is invalid, return the validation errors
        return Response({
            "error": "Validation failed",
            "details": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
class DocumentCategoryView(APIView):
    def get(self, request):
        """List all document categories"""
        categories = DocumentVerificationCategory.objects.all()
        serializer = DocumentVerificationCategorySerializer(categories, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create new document category with documents"""
        # Create the document category first
        serializer = DocumentVerificationCategorySerializer(data=request.data)
        if serializer.is_valid():
            category = serializer.save()

            # Now create the associated documents if needed
            document_ids = request.data.get('documents', [])
            documents = Document.objects.filter(id__in=document_ids)
            category.documents.set(documents)
            
            return Response({
                "message": "Document category created successfully",
                "data": DocumentVerificationCategorySerializer(category).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class ProviderDocumentUploadView(APIView):
    """
    View to upload documents for a provider.
    """
    def post(self, request):
        serializer = ProviderDocumentSerializer(data=request.data)
        if serializer.is_valid():
            # Automatically set the file size after file upload
            file = request.FILES.get('file')
            if file:
                serializer.validated_data['file_size'] = f"{round(file.size / 1024, 2)} KB"
            serializer.save()
            return Response({"message": "Document uploaded successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProviderDocumentsListView(APIView):
    """
    View to list all documents uploaded by a specific provider.
    """
    def post(self, request):
        auth_user_id = request.data.get('auth_user_id')
        if not auth_user_id:
            return Response({"error": "auth_user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        documents = ProviderDocument.objects.filter(verified_user__auth_user_id=auth_user_id)
        if not documents.exists():
            return Response({"message": "No documents found for this provider"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProviderDocumentSerializer(documents, many=True)
        return Response({"documents": serializer.data}, status=status.HTTP_200_OK)


class DocumentVerificationUpdateView(APIView):
    """
    View to verify a document by admin.
    """
    def post(self, request):
        doc_id = request.data.get("doc_id")
        if not doc_id:
            return Response({"error": "doc_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        document = get_object_or_404(ProviderDocument, id=doc_id)
        document.verification_status = request.data.get("verification_status", "pending")
        document.remarks = request.data.get("remarks", "")
        document.verified_by = request.data.get("verified_by", "system")
        document.verified_at = timezone.now()
        document.save()

        # Log the verification
        AutoVerificationLog.objects.create(
            provider_document=document,
            verification_source="manual_verification",
            response_status=document.verification_status,
            response_data={"remarks": document.remarks, "verified_by": document.verified_by}
        )

        return Response({"message": "Document verification updated", "document": ProviderDocumentSerializer(document).data}, status=status.HTTP_200_OK)