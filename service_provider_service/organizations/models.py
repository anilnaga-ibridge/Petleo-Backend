import uuid
from django.db import models
from service_provider.models import VerifiedUser


class OrganizationProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    owner = models.OneToOneField(
        VerifiedUser,
        on_delete=models.CASCADE,
        to_field="auth_user_id",
        related_name="organization_profile"
    )

    business_name = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.business_name or "OrganizationProfile"
