import uuid
from django.db import models
from service_provider.models import VerifiedUser


class IndividualProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    verified_user = models.OneToOneField(
        VerifiedUser,
        on_delete=models.CASCADE,
        to_field="auth_user_id",
        related_name="individual_profile"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"IndividualProfile - {self.verified_user.full_name}"
