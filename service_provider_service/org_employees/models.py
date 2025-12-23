from django.db import models

# Create your models here.
import uuid
from django.db import models
from service_provider.models import VerifiedUser
from organizations.models import OrganizationProfile


class OrganizationEmployee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    organization = models.ForeignKey(
        OrganizationProfile,
        on_delete=models.CASCADE,
        related_name="employees"
    )

    verified_user = models.OneToOneField(
        VerifiedUser,
        on_delete=models.CASCADE,
        to_field="auth_user_id",
        related_name="employee_profile"
    )

    role = models.CharField(max_length=50, default="staff")

    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    permissions = models.JSONField(default=dict, blank=True)
    profile_data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.verified_user.full_name} - {self.role}"


def employee_doc_upload_path(instance, filename):
    return f"org_employees/{instance.employee.id}/documents/{filename}"


class EmployeeDocument(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        OrganizationEmployee,
        on_delete=models.CASCADE,
        related_name="documents"
    )
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to=employee_doc_upload_path)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.employee.verified_user.full_name}"


class EmployeeServiceSubscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        OrganizationEmployee,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )
    service = models.ForeignKey(
        "provider_dynamic_fields.ProviderTemplateService",
        on_delete=models.CASCADE,
        related_name="employee_subscriptions"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'service')

    def __str__(self):
        return f"{self.employee.verified_user.full_name} - {self.service.display_name}"
