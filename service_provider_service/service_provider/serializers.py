from rest_framework import serializers
from .models import ServiceProvider

class ServiceProviderSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='verified_user.full_name', read_only=True)
    email = serializers.EmailField(source='verified_user.email', read_only=True)
    phone_number = serializers.CharField(source='verified_user.phone_number', read_only=True)
    auth_user_id = serializers.UUIDField(source='verified_user.auth_user_id', read_only=True)

    class Meta:
        model = ServiceProvider
        fields = ['id', 'auth_user_id', 'full_name', 'email', 'phone_number', 'profile_status', 'avatar', 'is_fully_verified']


from .models import OrganizationEmployee, VerifiedUser

class OrganizationEmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationEmployee
        fields = ['id', 'auth_user_id', 'status', 'joined_at', 'full_name', 'email', 'phone_number', 'role']


