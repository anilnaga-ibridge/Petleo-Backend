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
    organization_name = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()
    employee_avatar_url = serializers.SerializerMethodField()
    organization_avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationEmployee
        fields = [
            'id', 'auth_user_id', 'status', 'joined_at', 'full_name', 
            'email', 'phone_number', 'role', 'provider_role', 'provider_role_name',
            'permissions_json', 'average_rating', 'total_ratings',
            'specialization', 'consultation_fee', 'organization_name', 'capabilities',
            'employee_avatar_url', 'organization_avatar_url'
        ]

    def get_organization_name(self, obj):
        try:
            return obj.organization.verified_user.full_name
        except:
            return "Unknown Organization"

    def get_capabilities(self, obj):
        try:
            # Get the final intersection of Plan and Role permissions
            perms = obj.get_final_permissions()
            return sorted(list(perms.keys()))
        except:
            return []

    def get_employee_avatar_url(self, obj):
        try:
            user = VerifiedUser.objects.filter(auth_user_id=obj.auth_user_id).first()
            if not user or not user.avatar_url:
                return None
            
            # If already absolute, return as is
            if user.avatar_url.startswith('http'):
                return user.avatar_url
            
            # Prepend host if request is in context
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(user.avatar_url)
            
            return user.avatar_url
        except:
            return None

    def get_organization_avatar_url(self, obj):
        try:
            url = None
            if obj.organization.avatar:
                url = obj.organization.avatar.url
            elif obj.organization.verified_user.avatar_url:
                url = obj.organization.verified_user.avatar_url
            
            if not url:
                return None
            
            if url.startswith('http'):
                return url
            
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
            
            return url
        except:
            return None


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
    auth_user_id = serializers.UUIDField(source='verified_user.auth_user_id', read_only=True)
    
    # Location
    location = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()

    class Meta:
        model = ServiceProvider
        fields = ['id', 'auth_user_id', 'full_name', 'role', 'avatar', 'location', 'services', 'profile_status', 'average_rating', 'total_ratings']

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
         # Return only active employees
         employees = obj.employees.filter(status='ACTIVE', deleted_at__isnull=True)
         request = self.context.get("request")
         
         from service_provider.models import VerifiedUser
         
         employee_data = []
         for e in employees:
             avatar_url = None
             
             # Fetch the VerifiedUser to get the avatar URL
             try:
                 vu = VerifiedUser.objects.filter(auth_user_id=e.auth_user_id).first()
                 if vu and vu.avatar_url:
                      # avatar_url is typically already an absolute S3/Cloudinary URL, 
                      # but if it's relative, build an absolute uri
                      if request and not vu.avatar_url.startswith('http'):
                          avatar_url = request.build_absolute_uri(vu.avatar_url)
                      else:
                          avatar_url = vu.avatar_url
             except Exception:
                 pass

             employee_data.append({
                 "id": str(e.id),
                 "auth_user_id": str(e.auth_user_id),
                 "full_name": e.full_name,
                 "role": e.provider_role.name if e.provider_role else e.role,
                 "specialization": e.specialization,
                 "consultation_fee": e.consultation_fee,
                 "average_rating": e.average_rating,
                 "total_ratings": e.total_ratings,
                 "avatar": avatar_url
             })
         return employee_data

        
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
    capability_actions = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = ProviderRole
        fields = ['id', 'provider', 'name', 'description', 'is_system_role', 'capabilities', 'capability_actions', 'employees', 'created_at']
        read_only_fields = ['provider', 'is_system_role', 'employees', 'created_at']


    def to_representation(self, instance):
        ret = super().to_representation(instance)
        
        # 🛡️ Robust Model Resolution
        from django.apps import apps
        CapabilityModel = apps.get_model('service_provider', 'Capability')
        
        # 1. Capabilities with Labels and Granular Flags
        cap_actions = instance.capabilities.all()
        cap_keys = [c.capability_key for c in cap_actions]
        
        # Build a map of capabilities for easy lookup
        caps_map = {c.key: c for c in CapabilityModel.objects.filter(key__in=cap_keys)}
        
        details = []
        for action in cap_actions:
            cap_obj = caps_map.get(action.capability_key)
            details.append({
                "key": action.capability_key,
                "label": cap_obj.label if cap_obj else action.capability_key,
                "group": cap_obj.group if cap_obj else "General",
                "can_view": action.can_view,
                "can_create": action.can_create,
                "can_edit": action.can_edit,
                "can_delete": action.can_delete
            })
            
        ret['capabilities_details'] = details
        ret['capabilities'] = cap_keys 
        
        # Compatibility for expanded dashboard
        ret['capability_actions'] = details

        # 2. Employees with Names/Emails
        emps = instance.employees.all()
        ret['employees_details'] = [
            {"full_name": e.full_name, "email": e.email} for e in emps
        ]
        
        return ret

    def _save_capabilities(self, role, capabilities_data=None, capability_actions=None):
        """Helper to save capabilities with granular permissions."""
        from .models import ProviderRoleCapability
        
        # If capability_actions is provided, use it (Granular support)
        if capability_actions is not None:
            role.capabilities.all().delete()
            for action in capability_actions:
                ProviderRoleCapability.objects.create(
                    provider_role=role,
                    capability_key=action.get('capability_key'),
                    can_view=action.get('can_view', False),
                    can_create=action.get('can_create', False),
                    can_edit=action.get('can_edit', False),
                    can_delete=action.get('can_delete', False)
                )
        # Fallback to legacy flat list (all True or View only depending on logic)
        elif capabilities_data is not None:
            role.capabilities.all().delete()
            for cap_key in set(capabilities_data):
                ProviderRoleCapability.objects.create(
                    provider_role=role, 
                    capability_key=cap_key,
                    can_view=True,
                    can_create=True,
                    can_edit=True,
                    can_delete=True
                )

    def create(self, validated_data):
        capabilities_data = validated_data.pop('capabilities', None)
        capability_actions = validated_data.pop('capability_actions', None)
        
        role = ProviderRole.objects.create(**validated_data)
        self._save_capabilities(role, capabilities_data, capability_actions)
        return role

    def update(self, instance, validated_data):
        capabilities_data = validated_data.pop('capabilities', None)
        capability_actions = validated_data.pop('capability_actions', None)
        
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.save()
        
        if capabilities_data is not None or capability_actions is not None:
            self._save_capabilities(instance, capabilities_data, capability_actions)
        
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
    auth_user_id = serializers.UUIDField(source='verified_user.auth_user_id', read_only=True)
    
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
            'id', 'auth_user_id', 'providerName', 'providerType', 'avatar', 'banner_image',
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
            request = self.context.get("request")
            user_target = getattr(obj, 'verified_user', obj)
            return _build_permission_tree(user_target, request=request)
        except Exception as e:
            print(f"MENU ERROR (ProfileSerializer): {e}")
            return []

    def get_bio(self, obj):
        if hasattr(obj, 'detailed_profile'):
            return obj.detailed_profile.about_text
        
        # Handle cases where obj is either a ServiceProvider or just a VerifiedUser
        name = getattr(obj, 'full_name', None)
        if not name and hasattr(obj, 'verified_user'):
            name = obj.verified_user.full_name
            
        return f"Welcome to {name or 'our clinic'}!"

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
