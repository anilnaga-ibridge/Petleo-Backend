
from rest_framework import serializers
from .models import (
    Clinic, PetOwner, Pet, Visit, 
    DynamicFieldDefinition, DynamicFieldValue,
    FormDefinition, FormField, FieldValidation, FormSubmission,
    PharmacyDispense, MedicationReminder
)
from .services import DynamicEntityService

class ClinicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinic
        fields = '__all__'

class PetOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetOwner
        fields = '__all__'

class PetSerializer(serializers.ModelSerializer):
    dynamic_data = serializers.SerializerMethodField()

    class Meta:
        model = Pet
        fields = ['id', 'owner', 'name', 'species', 'breed', 'created_at', 'updated_at', 'dynamic_data']

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
    
    class Meta:
        model = Visit
        fields = ['id', 'clinic', 'pet', 'pet_id', 'status', 'created_at', 'updated_at', 'vitals']

    def get_vitals(self, obj):
        return DynamicEntityService.get_entity_data(obj.id, 'VITALS')

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

class FormDefinitionSerializer(serializers.ModelSerializer):
    fields = FormFieldSerializer(many=True, read_only=True)

    class Meta:
        model = FormDefinition
        fields = '__all__'

class FormSubmissionSerializer(serializers.ModelSerializer):
    form_name = serializers.CharField(source='form_definition.name', read_only=True)
    form_code = serializers.CharField(source='form_definition.code', read_only=True)

    class Meta:
        model = FormSubmission
        fields = '__all__'

    class Meta:
        model = FormSubmission
        fields = '__all__'

# ========================
# PHASE 3: EXECUTION SERIALIZERS
# ========================

class PharmacyDispenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacyDispense
        fields = '__all__'

class MedicationReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicationReminder
        fields = '__all__'

class VisitDetailSerializer(VisitSerializer):
    """
    Detailed serializer for Doctor's view (includes form submissions)
    """
    submissions = FormSubmissionSerializer(source='form_submissions', many=True, read_only=True)
    dispenses = PharmacyDispenseSerializer(many=True, read_only=True)
    reminders = MedicationReminderSerializer(many=True, read_only=True)
    
    class Meta(VisitSerializer.Meta):
        fields = VisitSerializer.Meta.fields + ['submissions', 'dispenses', 'reminders']
