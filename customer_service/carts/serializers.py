from rest_framework import serializers
from .models import Cart, CartItem
from pets.serializers import PetSerializer

class CartItemSerializer(serializers.ModelSerializer):
    pet_details = PetSerializer(source='pet', read_only=True)
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'provider_id', 'provider_auth_id', 'pet', 'pet_details', 
            'service_id', 'facility_id', 'employee_id', 'selected_time', 
            'selected_addons', 'extra_notes', 'price_snapshot', 'service_snapshot', 'created_at'
        ]

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(source='items.count', read_only=True)
    
    class Meta:
        model = Cart
        fields = ['id', 'owner', 'items', 'item_count', 'updated_at']
