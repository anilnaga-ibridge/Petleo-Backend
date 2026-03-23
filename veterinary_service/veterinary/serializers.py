from rest_framework import serializers
from .models import (
    StaffClinicAssignment, Clinic, PetOwner, Pet, Visit, 
    DynamicFieldDefinition, DynamicFieldValue, # Retain DynamicFieldValue
    FormDefinition, FormField, FieldValidation, FormSubmission, # Retain FieldValidation
    PharmacyDispense, MedicineReminder, MedicineReminderSchedule, VisitInvoice, InvoiceLineItem,
    LabTestTemplate, LabTestField, LabOrder, LabResult, MedicalAppointment,
    LabTest, Medicine, MedicineBatch, Prescription, PrescriptionItem, PharmacyTransaction
)
from .services import DynamicEntityService

class LabTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTest
        fields = '__all__'

class LabTestFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTestField
        fields = ['id', 'field_name', 'unit', 'min_value', 'max_value', 'order']

class LabTestTemplateSerializer(serializers.ModelSerializer):
    fields = LabTestFieldSerializer(many=True, required=False)

    class Meta:
        model = LabTestTemplate
        fields = ['id', 'name', 'is_active', 'fields']

    def update(self, instance, validated_data):
        fields_data = validated_data.pop('fields', None)
        instance.name = validated_data.get('name', instance.name)
        instance.is_active = validated_data.get('is_active', instance.is_active)
        instance.save()

        if fields_data is not None:
            instance.fields.all().delete()
            for field_data in fields_data:
                LabTestField.objects.create(template=instance, **field_data)
        return instance

    def create(self, validated_data):
        fields_data = validated_data.pop('fields', [])
        template = LabTestTemplate.objects.create(**validated_data)
        for field_data in fields_data:
            LabTestField.objects.create(template=template, **field_data)
        return template

class MedicineBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicineBatch
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class MedicineSerializer(serializers.ModelSerializer):
    batches = MedicineBatchSerializer(many=True, read_only=True)
    
    class Meta:
        model = Medicine
        fields = '__all__'
        read_only_fields = ['id', 'clinic', 'created_at', 'updated_at']

class PrescriptionItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    class Meta:
        model = PrescriptionItem
        fields = '__all__'

class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True, read_only=True)
    pet_name = serializers.CharField(source='visit.pet.name', read_only=True)
    
    class Meta:
        model = Prescription
        fields = '__all__'

class PharmacyTransactionSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    class Meta:
        model = PharmacyTransaction
        fields = '__all__'

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
    pet_photo = serializers.SerializerMethodField()

    class Meta:
        model = Pet
        fields = ['id', 'owner', 'name', 'species', 'breed', 'sex', 'dob', 'color', 'weight', 'notes', 'tag', 'profile_image', 'is_active', 'created_at', 'updated_at', 'dynamic_data', 'pet_photo']
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at', 'dynamic_data', 'pet_photo']

    def get_pet_photo(self, obj):
        # Return a high-quality placeholder if no photo is present in dynamic_data
        data = DynamicEntityService.get_entity_data(obj.id, 'PET')
        if data.get('photo_url'):
            return data.get('photo_url')
        
        # Default placeholder matching the mockup's vibe
        return "https://images.unsplash.com/photo-1552053831-71594a27632d?auto=format&fit=crop&q=80&w=150"

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
    latest_prescription = serializers.SerializerMethodField()
    provider_id = serializers.CharField(source='clinic.organization_id', read_only=True)
    assigned_employee_id = serializers.CharField(source='created_by', read_only=True)
    consultation_mode = serializers.SerializerMethodField()
    meeting_room = serializers.SerializerMethodField()
    
    class Meta:
        model = Visit
        fields = [
            'id', 'clinic', 'provider_id', 'pet', 'pet_id', 'service_id', 
            'status', 'visit_type', 'reason', 'priority', 'triage_notes', 
            'queue_entered_at', 'assigned_doctor_auth_id', 'created_at', 'updated_at', 
            'vitals', 'latest_lab_order', 'latest_prescription', 'checked_in_at', 'vitals_started_at', 
            'vitals_completed_at', 'doctor_started_at', 'closed_at', 'assigned_employee_id',
            'consultation_mode', 'meeting_room'
        ]
        read_only_fields = [
            'id', 'clinic', 'provider_id', 'checked_in_at', 'vitals_started_at', 
            'vitals_completed_at', 'doctor_started_at', 'closed_at', 'vitals', 
            'latest_lab_order', 'latest_prescription', 'assigned_employee_id', 'consultation_mode', 'meeting_room',
            'queue_entered_at'
        ]

    def get_consultation_mode(self, obj):
        # Link back to MedicalAppointment if possible
        appt = MedicalAppointment.objects.filter(visit=obj).first()
        return appt.consultation_mode if appt else 'CLINIC'

    def get_meeting_room(self, obj):
        appt = MedicalAppointment.objects.filter(visit=obj).first()
        return appt.meeting_room if appt else None

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

    def get_latest_prescription(self, obj):
        last_submission = FormSubmission.objects.filter(
            visit=obj, 
            form_definition__code='PRESCRIPTION'
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

class MedicineReminderScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicineReminderSchedule
        fields = '__all__'

class MedicineReminderSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    pet_name = serializers.CharField(source='pet.name', read_only=True)
    schedules = MedicineReminderScheduleSerializer(many=True, read_only=True)
    
    class Meta:
        model = MedicineReminder
        fields = '__all__'



class VisitDetailSerializer(VisitSerializer):
    """
    Detailed serializer for Doctor's view (includes form submissions)
    """
    submissions = FormSubmissionSerializer(source='form_submissions', many=True, read_only=True)
    dispenses = PharmacyDispenseSerializer(many=True, read_only=True)
    reminders = MedicineReminderSerializer(source='pet.medicine_reminders', many=True, read_only=True)
    
    class Meta(VisitSerializer.Meta):
        fields = VisitSerializer.Meta.fields + ['submissions', 'dispenses', 'reminders']


# ========================
# PHASE 4: BILLING SERIALIZERS
# ========================

class InvoiceLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLineItem
        fields = '__all__'

class VisitInvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceLineItemSerializer(many=True, read_only=True)

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
    staff_name = serializers.CharField(source='staff.full_name', read_only=True)
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    staff_auth_id = serializers.CharField(required=False)
    
    class Meta:
        from .models import StaffClinicAssignment
        model = StaffClinicAssignment
        fields = [
            'id', 'staff', 'clinic', 'role', 'permissions', 'staff_name', 
            'clinic_name', 'staff_auth_id', 'is_active', 'is_primary',
            'specialization', 'consultation_fee'
        ]
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
            
        # [FIX] Flatten permissions array if it contains dicts
        perms = validated_data.get('permissions', [])
        if perms and isinstance(perms, list) and len(perms) > 0 and isinstance(perms[0], dict):
            flat = []
            for p in perms:
                if 'capability_key' in p:
                    flat.append(p['capability_key'])
            validated_data['permissions'] = list(set(flat))
            
        # Upsert Logic
        assignment, created = StaffClinicAssignment.objects.update_or_create(
            staff=validated_data['staff'],
            clinic=validated_data['clinic'],
            defaults=validated_data
        )
        return assignment


class MedicalAppointmentSerializer(serializers.ModelSerializer):
    pet_name = serializers.CharField(source='pet.name', read_only=True)
    owner_name = serializers.CharField(source='pet.owner.name', read_only=True)
    owner_phone = serializers.CharField(source='pet.owner.phone', read_only=True)
    doctor_name = serializers.CharField(source='doctor.staff.full_name', read_only=True)
    visit_id = serializers.UUIDField(source='visit.id', read_only=True)
    visit_status = serializers.CharField(source='visit.status', read_only=True)
    pet_details = PetSerializer(source='pet', read_only=True)
    
    start_datetime = serializers.SerializerMethodField()
    end_datetime = serializers.SerializerMethodField()
    vitals = serializers.SerializerMethodField()
    
    class Meta:
        model = MedicalAppointment
        fields = '__all__'
        read_only_fields = ['id', 'clinic', 'end_time']

    def get_start_datetime(self, obj):
        if not obj.appointment_date or not obj.start_time:
            return None
        from django.utils import timezone
        import datetime
        dt = datetime.datetime.combine(obj.appointment_date, obj.start_time)
        return timezone.make_aware(dt)

    def get_end_datetime(self, obj):
        if not obj.appointment_date or not obj.end_time:
            return None
        from django.utils import timezone
        import datetime
        dt = datetime.datetime.combine(obj.appointment_date, obj.end_time)
        return timezone.make_aware(dt)

    def get_vitals(self, obj):
        # 1. Check if visit exists
        try:
            visit = obj.visit
        except:
            return {}

        if not visit:
            return {}
        
        # 2. Try latest VITALS form submission
        last_submission = FormSubmission.objects.filter(
            visit=visit, 
            form_definition__code='VITALS'
        ).order_by('-created_at').first()
        
        if last_submission:
            return last_submission.data
            
        # 3. Fallback: Legacy dynamic entity data (for vitals recorded on visit, not appt)
        return DynamicEntityService.get_entity_data(visit.id, 'VITALS')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            from .views import get_clinic_context
            clinic_id = get_clinic_context(request)
            if clinic_id:
                self.fields['pet'].queryset = Pet.objects.filter(owner__clinic_id=clinic_id)
                self.fields['doctor'].queryset = StaffClinicAssignment.objects.filter(clinic_id=clinic_id, role='DOCTOR')

# ========================
# PHASE 5: VACCINATION TRACKING SERIALIZERS
# ========================

class VaccineMasterSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import VaccineMaster
        model = VaccineMaster
        fields = '__all__'
        read_only_fields = ['id', 'clinic']

    def validate(self, attrs):
        request = self.context.get('request')
        from .views import get_clinic_context
        clinic_id = get_clinic_context(request)
        attrs['clinic_id'] = clinic_id
        return attrs

class PetVaccinationRecordSerializer(serializers.ModelSerializer):
    vaccine_name = serializers.CharField(source='vaccine.vaccine_name', read_only=True)
    species = serializers.CharField(source='vaccine.species', read_only=True)
    pet_name = serializers.CharField(source='pet.name', read_only=True)
    
    class Meta:
        from .models import PetVaccinationRecord
        model = PetVaccinationRecord
        fields = '__all__'
        read_only_fields = ['id', 'clinic', 'next_due_date']
        
    def validate(self, attrs):
        request = self.context.get('request')
        from .views import get_clinic_context
        clinic_id = get_clinic_context(request)
        attrs['clinic_id'] = clinic_id
        
        # Cross-check Pet and Vaccine belong to this clinic
        if 'pet' in attrs and str(attrs['pet'].owner.clinic_id) != str(clinic_id):
            raise serializers.ValidationError({"pet": "Pet does not belong to your clinic."})
            
        if 'vaccine' in attrs and str(attrs['vaccine'].clinic_id) != str(clinic_id):
            raise serializers.ValidationError({"vaccine": "Vaccine is not registered in your clinic's master list."})
            
        return attrs

class VaccinationReminderSerializer(serializers.ModelSerializer):
    pet_name = serializers.CharField(source='vaccination_record.pet.name', read_only=True)
    vaccine_name = serializers.CharField(source='vaccination_record.vaccine.vaccine_name', read_only=True)
    
    class Meta:
        from .models import VaccinationReminder
        model = VaccinationReminder
        fields = '__all__'

# ==========================================
# PHASE 6: ESTIMATE SERIALIZERS
# ==========================================

class EstimateLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import EstimateLineItem
        model = EstimateLineItem
        fields = '__all__'

class TreatmentEstimateSerializer(serializers.ModelSerializer):
    items = EstimateLineItemSerializer(many=True, read_only=True)
    pet_name = serializers.CharField(source='visit.pet.name', read_only=True)
    owner_name = serializers.CharField(source='visit.pet.owner.name', read_only=True)

    class Meta:
        from .models import TreatmentEstimate
        model = TreatmentEstimate
        fields = '__all__'
        read_only_fields = ['id', 'total_amount', 'created_at', 'updated_at']

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

# ==========================================
# PHASE 4: PRE-VISIT FORM SERIALIZERS
# ==========================================

class PreVisitFormSerializer(serializers.ModelSerializer):
    pet_name = serializers.CharField(source='visit.pet.name', read_only=True)
    owner_name = serializers.CharField(source='visit.pet.owner.name', read_only=True)
    visit_date = serializers.DateTimeField(source='visit.created_at', read_only=True)

    class Meta:
        from .models import PreVisitForm
        model = PreVisitForm
        fields = '__all__'
        read_only_fields = ['id', 'access_token', 'is_submitted', 'submitted_at', 'created_at']

# ==========================================
# PHASE 7: VACCINATION & DEWORMING REMINDER SYSTEM
# ==========================================
from .models import Vaccination, SystemVaccinationReminder, Deworming, SystemDewormingReminder

class SystemVaccinationReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemVaccinationReminder
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class VaccinationSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='visit.assigned_doctor_auth_id', read_only=True)
    
    class Meta:
        model = Vaccination
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class SystemDewormingReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemDewormingReminder
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class DewormingSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='visit.assigned_doctor_auth_id', read_only=True)
    
    class Meta:
        model = Deworming
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
