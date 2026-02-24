from rest_framework import serializers
from .models import (
    ServiceProvider, Capability, ProviderRole, ProviderRoleCapability, ProviderRating,
    ProviderProfile, ProviderService, ProviderServiceImage, ProviderCertification,
    ProviderGallery, ProviderPolicy
)

class ServiceProviderSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='verified_user.full_name', read_only=True)
    email = serializers.EmailField(source='verified_user.email', read_only=True)
    phone_number = serializers.CharField(source='verified_user.phone_number', read_only=True)
    auth_user_id = serializers.UUIDField(source='verified_user.auth_user_id', read_only=True)

    class Meta:
        model = ServiceProvider
        fields = ['id', 'auth_user_id', 'full_name', 'email', 'phone_number', 'profile_status', 'avatar', 'banner_image', 'banner_image_size', 'is_fully_verified']


from .models import OrganizationEmployee, VerifiedUser

class OrganizationEmployeeSerializer(serializers.ModelSerializer):
    provider_role_name = serializers.CharField(source='provider_role.name', read_only=True)

    class Meta:
        model = OrganizationEmployee
        fields = [
            'id', 'auth_user_id', 'status', 'joined_at', 'full_name', 
            'email', 'phone_number', 'role', 'provider_role', 'provider_role_name',
            'permissions_json', 'average_rating', 'total_ratings',
            'specialization', 'consultation_fee'
        ]


class ActiveProviderDTO(serializers.ModelSerializer):
    """
    DTO for the discovery marketplace screen.
    Matches specific requirements for the Discovery Flow.
    """
    providerId = serializers.UUIDField(source='id')
    providerName = serializers.CharField(source='verified_user.full_name')
    organizationName = serializers.SerializerMethodField()
    providerType = serializers.CharField(source='verified_user.role')
    city = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    profileImageUrl = serializers.ImageField(source='avatar')
    bannerImageUrl = serializers.ImageField(source='banner_image', required=False, allow_null=True)
    averageRating = serializers.SerializerMethodField()
    totalRatings = serializers.SerializerMethodField()
    servicesOffered = serializers.SerializerMethodField()

    class Meta:
        model = ServiceProvider
        fields = [
            'providerId', 'providerName', 'organizationName', 'providerType',
            'city', 'state', 'profileImageUrl', 'bannerImageUrl', 'averageRating', 'totalRatings', 'servicesOffered'
        ]

    def get_organizationName(self, obj):
        try:
             # Only return if role is organization (case-insensitive)
             role = obj.verified_user.role or ""
             if role.lower() == 'organization':
                 return getattr(obj.verified_user.billing_profile, 'company_name', None) or obj.verified_user.full_name
             return None
        except:
             return None

    def get_city(self, obj):
        from .utils import get_user_dynamic_location
        dynamic_loc = get_user_dynamic_location(obj.verified_user)
        if dynamic_loc:
            return dynamic_loc
            
        try:
             return obj.verified_user.billing_profile.contact
        except:
             return "Unknown"

    def get_state(self, obj):
        try:
             return obj.verified_user.billing_profile.state
        except:
             return ""

    def get_averageRating(self, obj):
        return obj.average_rating

    def get_totalRatings(self, obj):
        return obj.total_ratings

    def get_servicesOffered(self, obj):
        try:
             return list(obj.verified_user.allowed_services.values_list('name', flat=True))
        except:
             return []


class PublicProviderSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for the provider list (Marketplace Grid).
    """
    full_name = serializers.CharField(source='verified_user.full_name', read_only=True)
    role = serializers.CharField(source='verified_user.role', read_only=True)
    avatar = serializers.ImageField(read_only=True)
    
    # Location
    location = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()

    class Meta:
        model = ServiceProvider
        fields = ['id', 'full_name', 'role', 'avatar', 'location', 'services', 'profile_status', 'average_rating', 'total_ratings']

    def get_location(self, obj):
        from .utils import get_user_dynamic_location
        dynamic_loc = get_user_dynamic_location(obj.verified_user)
        if dynamic_loc:
            return dynamic_loc

        try:
            profile = obj.verified_user.billing_profile
            parts = []
            if profile.contact: parts.append(profile.contact)
            if profile.state: parts.append(profile.state)
            if profile.country: parts.append(profile.country)
            
            return ", ".join(parts) if parts else "Location not set"
        except Exception as e:
            return "Unknown Location"

    def get_services(self, obj):
        try:
             # Fetch service names this provider offers
             return list(obj.verified_user.allowed_services.values_list('name', flat=True))
        except:
             return []


class PublicProviderDetailSerializer(PublicProviderSerializer):
    """
    Detailed serializer for a specific provider (Profile Page).
    Includes the full service menu (Services -> Categories -> Facilities -> Prices).
    """
    bio = serializers.SerializerMethodField()
    menu = serializers.SerializerMethodField()
    email = serializers.EmailField(source='verified_user.email', read_only=True)
    phone_number = serializers.CharField(source='verified_user.phone_number', read_only=True)
    rating = serializers.FloatField(source='average_rating', read_only=True)
    review_count = serializers.IntegerField(source='total_ratings', read_only=True)
    address = serializers.SerializerMethodField()
    
    employees = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceProvider
        fields = PublicProviderSerializer.Meta.fields + ['bio', 'menu', 'email', 'phone_number', 'rating', 'review_count', 'address', 'employees']
        
    def get_employees(self, obj):
        try:
             # Return only active employees
             employees = obj.employees.filter(status='ACTIVE', deleted_at__isnull=True)
             return [
                 {
                     "id": str(e.id),
                     "auth_user_id": str(e.auth_user_id),
                     "full_name": e.full_name,
                     "role": e.provider_role.name if e.provider_role else e.role,
                     "specialization": e.specialization,
                     "consultation_fee": e.consultation_fee,
                     "average_rating": e.average_rating,
                     "total_ratings": e.total_ratings
                 }
                 for e in employees
             ]
        except:
             return []
        
    def get_address(self, obj):
        # Prefer direct location, fallback to billing contact
        loc = self.get_location(obj)
        if loc and loc not in ["Location not set", "Unknown Location", "PetLeo Member"]:
            return loc
            
        try:
             profile = obj.verified_user.billing_profile
             if profile.address:
                 return profile.address
        except:
             pass
             
        return loc
        
    def get_bio(self, obj):
        # Placeholder for bio, can be added to ServiceProvider model later
        return f"Welcome to {obj.verified_user.full_name or 'our clinic'}! We provide professional pet care services."

    def get_menu(self, obj):
        """
        Reconstruct the permission tree to show what services/facilities are offered.
        """
        from .utils import _build_permission_tree
        # Reuse existing logic to build the tree based on the provider's plan
        try:
            request = self.context.get("request")
            return _build_permission_tree(obj.verified_user, request=request)
        except Exception as e:
            print(f"Error building menu: {e}")
            return []





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
        # 1. Capabilities with Labels
        cap_keys = instance.capabilities.values_list('capability_key', flat=True)
        caps = Capability.objects.filter(key__in=cap_keys)
        ret['capabilities_details'] = [
            {"key": c.key, "label": c.label, "group": c.group} for c in caps
        ]
        ret['capabilities'] = cap_keys # Keep flat list for write compatibility

        # 2. Employees with Names/Emails
        emps = instance.employees.all()
        ret['employees_details'] = [
            {"full_name": e.full_name, "email": e.email} for e in emps
        ]
        
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


class ProviderRatingSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    assigned_employee_name = serializers.SerializerMethodField()
    service_name = serializers.SerializerMethodField()

    class Meta:
        model = ProviderRating
        fields = ['id', 'provider', 'customer_id', 'customer_name', 'service_id', 'service_name', 'assigned_employee_id', 'assigned_employee_name', 'rating', 'review', 'created_at', 'provider_response', 'responded_at']
        read_only_fields = ['id', 'created_at']

    def get_customer_name(self, obj):
        if obj.customer_name:
            return obj.customer_name
        return f"Pet Owner ({str(obj.customer_id)[:8]})"

    def get_service_name(self, obj):
        if not obj.service_id:
            return "General Review"
        try:
            from .models import AllowedService
            service = AllowedService.objects.filter(id=obj.service_id).first()
            return service.name if service else "Pet Care"
        except:
            return "Pet Care"

    def get_assigned_employee_name(self, obj):
        if not obj.assigned_employee_id:
            return None
        try:
            from .models import OrganizationEmployee
            emp = OrganizationEmployee.objects.filter(auth_user_id=obj.assigned_employee_id).first()
            return emp.full_name if emp else "Unknown Staff"
        except:
            return "Unknown Staff"


class ProviderProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderProfile
        fields = '__all__'
        read_only_fields = ['provider']


class ProviderServiceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderServiceImage
        fields = '__all__'
        read_only_fields = ['provider_service']


class ProviderServiceSerializer(serializers.ModelSerializer):
    images = ProviderServiceImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ProviderService
        fields = '__all__'
        read_only_fields = ['provider']


class ProviderCertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderCertification
        fields = '__all__'
        read_only_fields = ['provider']


class ProviderGallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderGallery
        fields = '__all__'
        read_only_fields = ['provider']


class ProviderPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderPolicy
        fields = '__all__'
        read_only_fields = ['provider']


class PublicProviderProfileSerializer(serializers.ModelSerializer):
    detailed_profile = ProviderProfileSerializer(read_only=True)
    custom_services = ProviderServiceSerializer(many=True, read_only=True)
    certifications = ProviderCertificationSerializer(many=True, read_only=True)
    gallery = ProviderGallerySerializer(many=True, read_only=True)
    policy = ProviderPolicySerializer(read_only=True)
    ratings = ProviderRatingSerializer(many=True, read_only=True)
    
    # Discovery fields
    providerName = serializers.CharField(source='verified_user.full_name', read_only=True)
    providerType = serializers.CharField(source='verified_user.role', read_only=True)
    averageRating = serializers.FloatField(source='average_rating', read_only=True)
    totalRatings = serializers.IntegerField(source='total_ratings', read_only=True)
    
    # New fields to match existing detail view expectations
    menu = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    email = serializers.EmailField(source='verified_user.email', read_only=True)
    phone_number = serializers.CharField(source='verified_user.phone_number', read_only=True)
    location = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    employees = serializers.SerializerMethodField()

    class Meta:
        model = ServiceProvider
        fields = [
            'id', 'providerName', 'providerType', 'avatar', 'banner_image',
            'averageRating', 'totalRatings', 'detailed_profile', 
            'custom_services', 'certifications', 'gallery', 'policy', 'ratings',
            'menu', 'bio', 'email', 'phone_number', 'location', 'address', 'employees'
        ]

    def get_employees(self, obj):
        # Delegate to PublicProviderDetailSerializer's logic
        return PublicProviderDetailSerializer().get_employees(obj)

    def get_address(self, obj):
        # Reuse logic from PublicProviderDetailSerializer if possible, 
        # but PublicProviderProfileSerializer doesn't inherit it.
        # Direct implementation:
        return self.get_location(obj)

    def get_menu(self, obj):
        from .utils import _build_permission_tree
        try:
            return _build_permission_tree(obj.verified_user)
        except:
            return []

    def get_bio(self, obj):
        if hasattr(obj, 'detailed_profile'):
            return obj.detailed_profile.about_text
        return f"Welcome to {obj.verified_user.full_name or 'our clinic'}!"

    def get_location(self, obj):
        from .utils import get_user_dynamic_location
        try:
            dynamic_loc = get_user_dynamic_location(obj.verified_user)
            if dynamic_loc:
                return dynamic_loc
            
            profile = obj.verified_user.billing_profile
            # BillingProfile doesn't have .city, it has .contact
            parts = [p for p in [profile.contact, profile.state] if p]
            return ", ".join(parts) or ""
        except:
            return ""
