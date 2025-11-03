from rest_framework import serializers
from .models import Pricing

class PricingSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.display_name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    facility_name = serializers.CharField(source="facility.name", read_only=True)

    class Meta:
        model = Pricing
        fields = "__all__"
