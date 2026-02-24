from rest_framework import serializers
from .models import Pet, PetMedicalProfile, PetDocument, PetMedication, PetVaccination


class PetMedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetMedication
        fields = [
            'id', 'name', 'dosage', 'frequency', 'reason', 
            'start_date', 'end_date', 'is_active', 'instructions', 'reminder_enabled'
        ]


class PetVaccinationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetVaccination
        fields = [
            'id', 'vaccine_name', 'date_administered', 'next_due_date', 
            'administered_by', 'batch_number', 'notes'
        ]


class PetMedicalProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetMedicalProfile
        fields = [
            'allergies', 'medical_conditions', 'last_vaccination_date', 
            'next_due_date', 'reminder_enabled', 'neutered', 'special_notes', 
            'vet_name', 'veterinarian', 'insurance_provider', 
            'insurance_policy_number', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class PetDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetDocument
        fields = [
            'id', 'document_name', 'document_type', 'file_url', 'file_type',
            'file_size', 'uploaded_by', 'verified_by_provider', 'verified_at',
            'uploaded_at'
        ]
        read_only_fields = ['id', 'file_type', 'file_size', 'verified_by_provider', 'verified_at', 'uploaded_at']


class PetSerializer(serializers.ModelSerializer):
    age_display = serializers.ReadOnlyField()
    medical_profile = PetMedicalProfileSerializer(required=False)
    medications = PetMedicationSerializer(many=True, read_only=True)
    vaccinations = PetVaccinationSerializer(many=True, read_only=True)
    
    class Meta:
        model = Pet
        fields = [
            'id', 'name', 'species', 'breed', 'gender', 'date_of_birth',
            'age_display', 'weight_kg', 'height_cm', 'blood_group', 
            'size_category', 'temperament', 'color', 'microchip_id', 
            'photo', 'status', 'is_active', 'created_at', 'updated_at', 
            'medical_profile', 'medications', 'vaccinations'
        ]
        read_only_fields = ['id', 'age_display', 'is_active', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        medical_profile_data = validated_data.pop('medical_profile', None)
        pet = Pet.objects.create(**validated_data)
        
        # Create medical profile if provided
        if medical_profile_data:
            PetMedicalProfile.objects.create(pet=pet, **medical_profile_data)
        else:
            # Create empty medical profile
            PetMedicalProfile.objects.create(pet=pet)
        
        return pet
    
    def update(self, instance, validated_data):
        medical_profile_data = validated_data.pop('medical_profile', None)
        
        # Update pet fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update medical profile if provided
        if medical_profile_data and hasattr(instance, 'medical_profile'):
            profile = instance.medical_profile
            for attr, value in medical_profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        
        return instance


class PetListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view"""
    age_display = serializers.ReadOnlyField()
    
    class Meta:
        model = Pet
        fields = [
            'id', 'name', 'species', 'breed', 'photo', 'age_display', 
            'status', 'is_active', 'gender', 'date_of_birth', 'color',
            'weight_kg', 'height_cm', 'blood_group'
        ]
