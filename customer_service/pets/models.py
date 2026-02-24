import uuid
from django.db import models
from django.utils import timezone
from datetime import date
from customers.models import PetOwnerProfile


from django.db.models import UniqueConstraint, Q, Index
from customer_service.models_base import SoftDeleteMixin
from customer_service.validators import validate_file_type, validate_file_size

class Pet(SoftDeleteMixin):
    """Pet model for storing pet information"""
    
    SPECIES_CHOICES = [
        ('DOG', 'Dog'),
        ('CAT', 'Cat'),
        ('BIRD', 'Bird'),
        ('OTHER', 'Other'),
    ]
    
    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
    ]

    SIZE_CATEGORY_CHOICES = [
        ('SMALL', 'Small'),
        ('MEDIUM', 'Medium'),
        ('LARGE', 'Large'),
        ('GIANT', 'Giant'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ARCHIVED', 'Archived'),
        ('DECEASED', 'Deceased'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(PetOwnerProfile, on_delete=models.CASCADE, related_name='pets')
    name = models.CharField(max_length=100)
    species = models.CharField(max_length=50) # Removed choices to allow dynamic IDs from superadmin
    breed = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    size_category = models.CharField(max_length=10, choices=SIZE_CATEGORY_CHOICES, default='MEDIUM')
    temperament = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=50, blank=True)
    microchip_id = models.CharField(max_length=50, blank=True, null=True)
    photo = models.ImageField(upload_to='pet_photos/', null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE')
    
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    blood_group = models.CharField(max_length=20, blank=True, help_text="e.g., DEA 1.1, A, B, etc.")
    
    is_active = models.BooleanField(default=True) # Legacy support
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            Index(fields=['owner', 'status']),
            Index(fields=['owner', 'species']),
        ]
        constraints = [
            UniqueConstraint(
                fields=['microchip_id'],
                condition=Q(deleted_at__isnull=True, microchip_id__isnull=False),
                name='unique_active_microchip_id'
            )
        ]
    
    def __str__(self):
        return f"{self.name} ({self.species})"
    
    @property
    def age_display(self):
        """Calculate a descriptive age string (e.g., '2 years', '6 months')"""
        if not self.date_of_birth:
            return "Unknown age"
        
        today = date.today()
        dob = self.date_of_birth
        
        years = today.year - dob.year
        months = today.month - dob.month
        
        if today.day < dob.day:
            months -= 1
            
        if months < 0:
            years -= 1
            months += 12
            
        if years > 0:
            if years == 1:
                return f"{years} year old"
            return f"{years} years old"
        else:
            if months == 1:
                return f"{months} month old"
            return f"{months} months old"


class PetMedicalProfile(models.Model):
    """Medical profile for pets"""
    
    pet = models.OneToOneField(Pet, on_delete=models.CASCADE, related_name='medical_profile')
    allergies = models.TextField(blank=True, help_text="List any known allergies")
    medical_conditions = models.TextField(blank=True, help_text="Existing medical conditions")
    
    # Summary fields (can be derived from related models but stored for quick access)
    last_vaccination_date = models.DateField(null=True, blank=True)
    next_due_date = models.DateField(null=True, blank=True)
    reminder_enabled = models.BooleanField(default=True)
    
    neutered = models.BooleanField(default=False)
    special_notes = models.TextField(blank=True, help_text="Any special care instructions")
    
    vet_name = models.CharField(max_length=100, blank=True)
    veterinarian = models.UUIDField(null=True, blank=True, help_text="UUID of associated business provider if any")
    
    insurance_provider = models.CharField(max_length=100, blank=True)
    insurance_policy_number = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Medical Profile for {self.pet.name}"


class PetMedication(models.Model):
    """Track current and past medications"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='medications')
    name = models.CharField(max_length=100)
    dosage = models.CharField(max_length=100, help_text="e.g., 5mg, 1 tablet")
    frequency = models.CharField(max_length=100, help_text="e.g., Twice daily, Every 8 hours")
    reason = models.CharField(max_length=255, blank=True)
    
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    instructions = models.TextField(blank=True)
    reminder_enabled = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} for {self.pet.name}"


class PetVaccination(models.Model):
    """Detailed vaccination records"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='vaccinations')
    vaccine_name = models.CharField(max_length=100)
    date_administered = models.DateField()
    next_due_date = models.DateField()
    
    administered_by = models.CharField(max_length=100, blank=True)
    batch_number = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.vaccine_name} for {self.pet.name}"


class PetDocument(models.Model):
    """Document storage for pet-related files"""
    
    DOCUMENT_TYPES = [
        ('VACCINATION', 'Vaccination Record'),
        ('DIAGNOSTIC_REPORT', 'Diagnostic Report'),
        ('MEDICAL_REPORT', 'Medical Report'),
        ('PRESCRIPTION', 'Prescription'),
        ('OTHER', 'Other'),
    ]

    UPLOADED_BY_CHOICES = [
        ('USER', 'User'),
        ('PROVIDER', 'Provider'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='documents')
    document_name = models.CharField(max_length=100, default='Document')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file_url = models.FileField(
        upload_to='pet_documents/',
        validators=[validate_file_type, validate_file_size]
    )
    file_type = models.CharField(max_length=50, blank=True) # e.g. application/pdf
    file_size = models.PositiveIntegerField(null=True, blank=True) # in bytes
    
    uploaded_by = models.CharField(max_length=10, choices=UPLOADED_BY_CHOICES, default='USER')
    verified_by_provider = models.UUIDField(null=True, blank=True) # UUID of provider who verified
    verified_at = models.DateTimeField(null=True, blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.document_name} for {self.pet.name}"
