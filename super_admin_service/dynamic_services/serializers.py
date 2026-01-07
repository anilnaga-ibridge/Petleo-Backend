from rest_framework import serializers
from .models import Service, Capability

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = "__all__"

class CapabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Capability
        fields = "__all__"
