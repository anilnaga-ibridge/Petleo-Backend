from rest_framework import serializers
from .models import ProviderCart, ProviderCartItem, PurchasedPlan


class ProviderCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderCartItem
        fields = "__all__"


class ProviderCartSerializer(serializers.ModelSerializer):
    items = ProviderCartItemSerializer(many=True, read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    auth_user_id = serializers.UUIDField(source='verified_user.auth_user_id', read_only=True)

    class Meta:
        model = ProviderCart
        fields = [
            "id",
            "auth_user_id",
            "status",
            "total_amount",
            "created_at",
            "updated_at",
            "items",
        ]


class PurchasedPlanSerializer(serializers.ModelSerializer):
    # Override verified_user to return the Auth Service ID instead of the internal Provider ID
    verified_user = serializers.UUIDField(source='verified_user.auth_user_id', read_only=True)
    auth_user_id = serializers.UUIDField(source='verified_user.auth_user_id', read_only=True)

    class Meta:
        model = PurchasedPlan
        fields = "__all__"
