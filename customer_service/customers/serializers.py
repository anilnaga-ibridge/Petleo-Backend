from rest_framework import serializers
from .models import PetOwnerProfile, PetOwnerAddress, FavoriteProvider

class PetOwnerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetOwnerAddress
        fields = [
            'id', 'address_line1', 'address_line2', 'city', 'state', 
            'pincode', 'latitude', 'longitude', 'is_default', 'address_type',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class FavoriteProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoriteProvider
        fields = ['id', 'provider_id', 'created_at']
        read_only_fields = ['id', 'created_at']

class PetOwnerProfileSerializer(serializers.ModelSerializer):
    addresses = PetOwnerAddressSerializer(many=True, read_only=True)
    
    class Meta:
        model = PetOwnerProfile
        fields = [
            'id', 'auth_user_id', 'full_name', 'phone_number', 'alternate_phone', 
            'email', 'profile_photo', 'preferred_language', 'emergency_contact_name', 
            'emergency_contact_phone', 'is_verified', 'bio', 'addresses',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'auth_user_id', 'is_verified', 'created_at', 'updated_at']
