from rest_framework import serializers
from .models import ServiceProvider, Capability, ProviderRole, ProviderRoleCapability

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
    provider_role_name = serializers.CharField(source='provider_role.name', read_only=True)

    class Meta:
        model = OrganizationEmployee
        fields = [
            'id', 'auth_user_id', 'status', 'joined_at', 'full_name', 
            'email', 'phone_number', 'role', 'provider_role', 'provider_role_name',
            'permissions_json'
        ]


class CapabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Capability
        fields = '__all__'


class ProviderRoleCapabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderRoleCapability
        fields = ['capability_key']


class ProviderRoleSerializer(serializers.ModelSerializer):
    capabilities = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = ProviderRole
        fields = ['id', 'provider', 'name', 'description', 'is_system_role', 'capabilities', 'employees', 'created_at']
        read_only_fields = ['provider', 'is_system_role', 'employees', 'created_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Serialize related capability keys
        ret['capabilities'] = instance.capabilities.values_list('capability_key', flat=True)
        return ret

    def create(self, validated_data):
        capabilities_data = list(set(validated_data.pop('capabilities', [])))
        role = ProviderRole.objects.create(**validated_data)
        for cap_key in capabilities_data:
            ProviderRoleCapability.objects.create(provider_role=role, capability_key=cap_key)
        return role

    def update(self, instance, validated_data):
        capabilities_data = validated_data.pop('capabilities', [])
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.save()
        
        # Update capabilities if provided
        if capabilities_data is not None:
             capabilities_data = list(set(capabilities_data))
             instance.capabilities.all().delete()
             for cap_key in capabilities_data:
                 ProviderRoleCapability.objects.create(provider_role=instance, capability_key=cap_key)
        
        return instance


