# admin_core/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from admin_core.models import VerifiedUser, AdminProfile

@receiver(post_save, sender=VerifiedUser)
def create_admin_profile(sender, instance, created, **kwargs):
    """
    Automatically create an AdminProfile for every new VerifiedUser with role='admin'
    """
    if created and instance.role == "admin":
        AdminProfile.objects.get_or_create(verified_user=instance)
