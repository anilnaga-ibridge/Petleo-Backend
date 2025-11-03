from rest_framework import serializers
from .models import Facility

class FacilitySerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.display_name", read_only=True)

    class Meta:
        model = Facility
        fields = "__all__"
