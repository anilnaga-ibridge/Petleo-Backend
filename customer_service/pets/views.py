from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Pet, PetMedicalProfile, PetDocument, PetMedication, PetVaccination
from .serializers import (
    PetSerializer, PetListSerializer, PetMedicalProfileSerializer, 
    PetDocumentSerializer, PetMedicationSerializer, PetVaccinationSerializer
)
from .permissions import IsOwner
from customers.models import PetOwnerProfile


class PetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Pet CRUD operations.
    Only the owner can create, edit, or delete their pets.
    """
    permission_classes = [IsAuthenticated, IsOwner]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PetListSerializer
        return PetSerializer
    def list(self, request, *args, **kwargs):
        print(f"DEBUG: PetViewSet.list called by {request.user}")
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        print(f"DEBUG: PetViewSet.get_queryset user={user} type={type(user)}")
        
        # Scenario 1: User IS a PetOwnerProfile (custom auth)
        if isinstance(user, PetOwnerProfile):
            return Pet.objects.filter(owner=user, is_active=True)
            
        # Scenario 2: User is a Django User with a linked profile
        if hasattr(user, 'petownerprofile'):
            return Pet.objects.filter(owner=user.petownerprofile, is_active=True)
            
        if hasattr(user, 'id'):
            print(f"DEBUG: Checking for profile with auth_user_id={user.id}")
            try:
                profile = PetOwnerProfile.objects.get(auth_user_id=user.id)
                print(f"DEBUG: Found profile {profile.id} for user {user.id}")
                return Pet.objects.filter(owner=profile, is_active=True)
            except PetOwnerProfile.DoesNotExist:
                print(f"DEBUG: Profile not found for auth_user_id={user.id}")
                pass

        print("DEBUG: User not resolved to PetOwnerProfile")
        return Pet.objects.none()
    
    def perform_create(self, serializer):
        # Automatically set the owner to the current user's profile
        if isinstance(self.request.user, PetOwnerProfile):
            serializer.save(owner=self.request.user)
        else:
            from rest_framework import serializers
            raise serializers.ValidationError("Pet owner profile not found")
    
    @action(detail=True, methods=['patch'], url_path='photo')
    def upload_photo(self, request, pk=None):
        """Endpoint for uploading pet photo"""
        pet = self.get_object()
        photo = request.FILES.get('photo')
        
        if not photo:
            return Response(
                {"error": "No photo provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        pet.photo = photo
        pet.save()
        
        serializer = self.get_serializer(pet)
        return Response(serializer.data)


class PetMedicalProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing pet medical profiles.
    Owner-only access.
    """
    serializer_class = PetMedicalProfileSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    
    def get_queryset(self):
        if isinstance(self.request.user, PetOwnerProfile):
            return PetMedicalProfile.objects.filter(pet__owner=self.request.user)
        return PetMedicalProfile.objects.none()


class PetMedicationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing pet medications"""
    serializer_class = PetMedicationSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    
    def get_queryset(self):
        if isinstance(self.request.user, PetOwnerProfile):
            pet_id = self.request.query_params.get('pet')
            queryset = PetMedication.objects.filter(pet__owner=self.request.user)
            if pet_id:
                queryset = queryset.filter(pet_id=pet_id)
            return queryset
        return PetMedication.objects.none()

    def perform_create(self, serializer):
        pet = serializer.validated_data.get('pet')
        if isinstance(self.request.user, PetOwnerProfile) and pet.owner != self.request.user:
            from rest_framework import serializers
            raise serializers.ValidationError("You can only manage medications for your own pets")
        serializer.save()


class PetVaccinationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing pet vaccinations"""
    serializer_class = PetVaccinationSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    
    def get_queryset(self):
        if isinstance(self.request.user, PetOwnerProfile):
            pet_id = self.request.query_params.get('pet')
            queryset = PetVaccination.objects.filter(pet__owner=self.request.user)
            if pet_id:
                queryset = queryset.filter(pet_id=pet_id)
            return queryset
        return PetVaccination.objects.none()

    def perform_create(self, serializer):
        pet = serializer.validated_data.get('pet')
        if isinstance(self.request.user, PetOwnerProfile) and pet.owner != self.request.user:
            from rest_framework import serializers
            raise serializers.ValidationError("You can only manage vaccinations for your own pets")
        serializer.save()


class PetDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing pet documents.
    Owner-only upload and view.
    """
    serializer_class = PetDocumentSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    
    def get_queryset(self):
        if isinstance(self.request.user, PetOwnerProfile):
            pet_id = self.request.query_params.get('pet')
            queryset = PetDocument.objects.filter(pet__owner=self.request.user)
            
            if pet_id:
                queryset = queryset.filter(pet_id=pet_id)
            
            return queryset
        return PetDocument.objects.none()
    
    def perform_create(self, serializer):
        # Validate that the pet belongs to the current user
        pet = serializer.validated_data.get('pet')
        if isinstance(self.request.user, PetOwnerProfile):
            if pet.owner != self.request.user:
                from rest_framework import serializers
                raise serializers.ValidationError("You can only upload documents for your own pets")
            
            # Extract and save metadata
            file = self.request.FILES.get('file_url')
            file_type = file.content_type if file else ''
            file_size = file.size if file else 0
            
            serializer.save(
                file_type=file_type,
                file_size=file_size,
                uploaded_by='USER'
            )
        else:
            from rest_framework import serializers
            raise serializers.ValidationError("Pet owner profile not found")
