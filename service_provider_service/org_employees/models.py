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

    def __str__(self):
        return f"{self.verified_user.full_name} - {self.role}"
