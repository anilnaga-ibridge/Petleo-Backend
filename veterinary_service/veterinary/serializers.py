
from rest_framework import serializers
from .models import (
    Clinic, PetOwner, Pet, Visit, 
    DynamicFieldDefinition, DynamicFieldValue,
    FormDefinition, FormField, FieldValidation, FormSubmission,
    PharmacyDispense, MedicationReminder, VisitInvoice, VisitCharge,
    LabTestTemplate, LabTestField, LabOrder, LabResult
)
from .services import DynamicEntityService

class ClinicSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Clinic
        fields = '__all__'
        read_only_fields = ['organization_id', 'is_primary']

    def get_permissions(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return []
        
        user = request.user
        role = str(getattr(user, 'role', '')).upper()

        if role in ['ORGANIZATION', 'INDIVIDUAL', 'PROVIDER', 'ORGANIZATION_PROVIDER', 'ORGANIZATION_ADMIN']:
            from .services import RolePermissionService
            return RolePermissionService.get_permissions_for_role('Admin', obj.organization_id)
        
        # 2. Staff get assigned permissions
        # Use auth_user_id (UUID)
        req_user_id = str(user.id)
        if hasattr(request.auth, 'get'):
             req_user_id = request.auth.get('user_id') or req_user_id

        # Ideally optimize this to avoid N+1 queries, but strictly scoped is safe
        try:
            from .models import StaffClinicAssignment
            assignment = StaffClinicAssignment.objects.filter(
                clinic=obj, 
                staff__auth_user_id=req_user_id,
                is_active=True
            ).first()
            if assignment:
                from .services import RolePermissionService
                return RolePermissionService.get_permissions_for_role(assignment.role, obj.organization_id)
        except Exception as e:
            # Fallback
            pass
            
        return []

class PetOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetOwner
        fields = '__all__'
        read_only_fields = ['clinic', 'created_by']

class PetSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(queryset=PetOwner.objects.all(), required=False)
    dynamic_data = serializers.SerializerMethodField()

    class Meta:
        model = Pet
        fields = ['id', 'owner', 'name', 'species', 'breed', 'sex', 'dob', 'color', 'weight', 'notes', 'tag', 'is_active', 'created_at', 'updated_at', 'dynamic_data']
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at', 'dynamic_data']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            from .views import get_clinic_context
            clinic_id = get_clinic_context(request)
            if clinic_id:
                self.fields['owner'].queryset = PetOwner.objects.filter(clinic_id=clinic_id)
            else:
                self.fields['owner'].queryset = PetOwner.objects.none()

    def update(self, instance, validated_data):
        from .permissions import log
        log(f"PetSerializer.update: Instance: {instance.id}, Validated Data: {validated_data}")
        # Ensure owner is NEVER changed via serializer update
        validated_data.pop('owner', None)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.owner:
            representation['owner'] = PetOwnerSerializer(instance.owner).data
        return representation

    def get_dynamic_data(self, obj):
        return DynamicEntityService.get_entity_data(obj.id, 'PET')

class DynamicFieldDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DynamicFieldDefinition
        fields = '__all__'

class DynamicFieldValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = DynamicFieldValue
        fields = '__all__'

class VisitSerializer(serializers.ModelSerializer):
    pet = PetSerializer(read_only=True)
    pet_id = serializers.UUIDField(write_only=True)
    vitals = serializers.SerializerMethodField()
    latest_lab_order = serializers.SerializerMethodField()
    
    class Meta:
        model = Visit
        fields = ['id', 'clinic', 'pet', 'pet_id', 'service_id', 'status', 'visit_type', 'reason', 'created_at', 'updated_at', 'vitals', 'latest_lab_order', 'checked_in_at', 'vitals_started_at', 'vitals_completed_at', 'doctor_started_at', 'closed_at']
        read_only_fields = ['id', 'clinic', 'checked_in_at', 'vitals_started_at', 'vitals_completed_at', 'doctor_started_at', 'closed_at', 'vitals', 'latest_lab_order']

    def validate(self, attrs):
        request = self.context.get('request')
        from .views import get_clinic_context
        clinic_id = get_clinic_context(request)
        
        pet_id = attrs.get('pet_id')
        if pet_id:
            from .models import Pet
            try:
                # Ensure the pet belongs to a PetOwner in the current clinic
                pet = Pet.objects.get(id=pet_id, owner__clinic_id=clinic_id)
                attrs['pet'] = pet
            except Pet.DoesNotExist:
                raise serializers.ValidationError({"pet_id": "Pet not found in this clinic context."})
        
        return attrs

    def get_vitals(self, obj):
        # 1. Try latest VITALS form submission first (New Engine)
        last_submission = FormSubmission.objects.filter(
            visit=obj, 
            form_definition__code='VITALS'
        ).order_by('-created_at').first()
        
        if last_submission:
            return last_submission.data
            
        # 2. Fallback: Legacy dynamic entity data
        return DynamicEntityService.get_entity_data(obj.id, 'VITALS')

    def get_latest_lab_order(self, obj):
        last_submission = FormSubmission.objects.filter(
            visit=obj, 
            form_definition__code='LAB_ORDER'
        ).order_by('-created_at').first()
        
        if last_submission:
            return last_submission.data
        return {}

class DynamicEntitySerializer(serializers.Serializer):
    """
    Generic serializer for creating/updating dynamic entities (Virtual or Real).
    Expects:
    - entity_type (e.g., 'PRESCRIPTION')
    - data (JSON dict of key-value pairs)
    """
    entity_type = serializers.CharField()
    data = serializers.DictField()

# ========================
# PHASE 2: METADATA SERIALIZERS
# ========================

class FieldValidationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldValidation
        fields = '__all__'

class FormFieldSerializer(serializers.ModelSerializer):
    validations = FieldValidationSerializer(many=True, read_only=True)

    class Meta:
        model = FormField
        fields = '__all__'
        extra_kwargs = {
            'form_definition': {'required': False}
        }
        validators = [] # Remove UniqueTogetherValidator to allow nested UPSERT logic in parent

class FormDefinitionSerializer(serializers.ModelSerializer):
    fields = FormFieldSerializer(many=True, required=False) # Changed from read_only=True

    class Meta:
        model = FormDefinition
        fields = '__all__'

    def update(self, instance, validated_data):
        fields_data = validated_data.pop('fields', None)
        
        # Update FormDefinition itself
        instance = super().update(instance, validated_data)
        
        # Update or Create nested fields
        if fields_data is not None:
            incoming_keys = [f.get('field_key') for f in fields_data if f.get('field_key')]
            
            # 1. Delete fields not in incoming payload
            # Important: Only delete if they belong to this form definition
            instance.fields.exclude(field_key__in=incoming_keys).delete()

            # 2. Update or Create remaining fields
            for field_item in fields_data:
                field_key = field_item.get('field_key')
                if not field_key:
                    continue
                
                field_obj, created = FormField.objects.update_or_create(
                    form_definition=instance,
                    field_key=field_key,
                    defaults={
                        'label': field_item.get('label', ''),
                        'field_type': field_item.get('field_type', 'TEXT'),
                        'unit': field_item.get('unit'),
                        'is_required': field_item.get('is_required', False),
                        'order': field_item.get('order', 0),
                        'metadata': field_item.get('metadata', {})
                    }
                )
        instance.refresh_from_db()
        return instance

class FormSubmissionSerializer(serializers.ModelSerializer):
    form_name = serializers.CharField(source='form_definition.name', read_only=True)
    form_code = serializers.CharField(source='form_definition.code', read_only=True)

    class Meta:
        model = FormSubmission
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            from .views import get_clinic_context
            clinic_id = get_clinic_context(request)
            if clinic_id:
                self.fields['visit'].queryset = Visit.objects.filter(clinic_id=clinic_id)
            else:
                self.fields['visit'].queryset = Visit.objects.none()

# ========================
# PHASE 3: EXECUTION SERIALIZERS
# ========================

class PharmacyDispenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacyDispense
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            from .views import get_clinic_context
            clinic_id = get_clinic_context(request)
            if clinic_id:
                self.fields['visit'].queryset = Visit.objects.filter(clinic_id=clinic_id)
                self.fields['prescription_submission'].queryset = FormSubmission.objects.filter(visit__clinic_id=clinic_id)
            else:
                self.fields['visit'].queryset = Visit.objects.none()
                self.fields['prescription_submission'].queryset = FormSubmission.objects.none()

class MedicationReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicationReminder
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            from .views import get_clinic_context
            clinic_id = get_clinic_context(request)
            if clinic_id:
                self.fields['visit'].queryset = Visit.objects.filter(clinic_id=clinic_id)
                self.fields['pet'].queryset = Pet.objects.filter(owner__clinic_id=clinic_id)
            else:
                self.fields['visit'].queryset = Visit.objects.none()
                self.fields['pet'].queryset = Pet.objects.none()

class VisitDetailSerializer(VisitSerializer):
    """
    Detailed serializer for Doctor's view (includes form submissions)
    """
    submissions = FormSubmissionSerializer(source='form_submissions', many=True, read_only=True)
    dispenses = PharmacyDispenseSerializer(many=True, read_only=True)
    reminders = MedicationReminderSerializer(many=True, read_only=True)
    
    class Meta(VisitSerializer.Meta):
        fields = VisitSerializer.Meta.fields + ['submissions', 'dispenses', 'reminders']


# ========================
# PHASE 4: BILLING SERIALIZERS
# ========================

class VisitChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitCharge
        fields = '__all__'

class VisitInvoiceSerializer(serializers.ModelSerializer):
    charges = VisitChargeSerializer(many=True, read_only=True)

    class Meta:
        model = VisitInvoice
        fields = '__all__'

# ========================
# PHASE 3.5: PROFESSIONAL LAB SERIALIZERS
# ========================

class LabTestFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTestField
        fields = '__all__'
        read_only_fields = ['template']

class LabTestTemplateSerializer(serializers.ModelSerializer):
    fields = LabTestFieldSerializer(many=True, read_only=True)
    
    class Meta:
        model = LabTestTemplate
        fields = '__all__'

class LabResultSerializer(serializers.ModelSerializer):
    field_name = serializers.CharField(source='test_field.field_name', read_only=True)
    unit = serializers.CharField(source='test_field.unit', read_only=True)
    min_value = serializers.FloatField(source='test_field.min_value', read_only=True)
    max_value = serializers.FloatField(source='test_field.max_value', read_only=True)

    class Meta:
        model = LabResult
        fields = '__all__'
        read_only_fields = ['flag'] # Flag is calculated by backend usually

class LabOrderSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    results = LabResultSerializer(many=True, read_only=True)
    pet_name = serializers.CharField(source='visit.pet.name', read_only=True)
    owner_name = serializers.CharField(source='visit.pet.owner.name', read_only=True)

    class Meta:
        model = LabOrder
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            from .views import get_clinic_context
            clinic_id = get_clinic_context(request)
            if clinic_id:
                self.fields['visit'].queryset = Visit.objects.filter(clinic_id=clinic_id)
            else:
                self.fields['visit'].queryset = Visit.objects.none()

class StaffClinicAssignmentSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.auth_user_id', read_only=True)
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    staff_auth_id = serializers.CharField(required=False)
    
    class Meta:
        from .models import StaffClinicAssignment
        model = StaffClinicAssignment
        fields = '__all__'
        extra_kwargs = {
            'permissions': {'required': False},
            'staff': {'required': False} # We derive this from staff_auth_id
        }
        # Disable default unique_together validator to allow manual upsert handling
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            user = request.user
            org_id = str(user.id)
            if hasattr(request.auth, 'get'):
                 org_id = request.auth.get('user_id') or org_id
            from .models import Clinic
            self.fields['clinic'].queryset = Clinic.objects.filter(organization_id=org_id)


    def validate(self, attrs):
        # 1. Resolve Staff
        staff_auth_id = attrs.get('staff_auth_id')
        staff = attrs.get('staff')
        
        if not staff and staff_auth_id:
            from .models import VeterinaryStaff
            staff_obj, created = VeterinaryStaff.objects.get_or_create(auth_user_id=staff_auth_id)
            attrs['staff'] = staff_obj
            
        if not attrs.get('staff'):
             raise serializers.ValidationError({"staff": "Staff ID or Auth ID is required."})

        # 2. Auto-populate permissions based on role
        role = attrs.get('role')
        if role and not attrs.get('permissions'):
            from .services import RolePermissionService
            clinic = attrs.get('clinic')
            org_id = str(clinic.organization_id) if clinic else None
            attrs['permissions'] = RolePermissionService.get_permissions_for_role(role, org_id)
            
        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['staff_auth_id'] = instance.staff.auth_user_id
        return ret

    def create(self, validated_data):
        from .models import StaffClinicAssignment
        
        # Remove write-only fields
        if 'staff_auth_id' in validated_data:
            validated_data.pop('staff_auth_id')
            
        # Upsert Logic
        assignment, created = StaffClinicAssignment.objects.update_or_create(
            staff=validated_data['staff'],
            clinic=validated_data['clinic'],
            defaults=validated_data
        )
        return assignment
