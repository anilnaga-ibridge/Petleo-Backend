# from django.contrib.auth.models import AbstractUser
# from django.db import models

# class Permission(models.Model):
#     codename = models.CharField(max_length=100, unique=True)
#     description = models.TextField(blank=True)

#     def __str__(self):
#         return self.codename


# class Role(models.Model):
#     name = models.CharField(max_length=50, unique=True)
#     description = models.TextField(blank=True)
#     permissions = models.ManyToManyField(Permission, blank=True)

#     def __str__(self):
#         return self.name


# class User(AbstractUser):
#     role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
#     token_version = models.IntegerField(default=0)

#     def has_permission(self, codename):
#         if not self.role:
#             return False
#         return self.role.permissions.filter(codename=codename).exists()
# import uuid
# from django.contrib.auth.models import AbstractUser
# from django.db import models

# class Permission(models.Model):
#     codename = models.CharField(max_length=100, unique=True)
#     description = models.TextField(blank=True)

#     def __str__(self):
#         return self.codename


# class Role(models.Model):
#     name = models.CharField(max_length=50, unique=True)
#     description = models.TextField(blank=True)
#     permissions = models.ManyToManyField(Permission, blank=True)

#     def __str__(self):
#         return self.name


# class User(AbstractUser):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
#     token_version = models.IntegerField(default=0)

#     def has_permission(self, codename):
#         if not self.role:
#             return False
#         return self.role.permissions.filter(codename=codename).exists()



# =====================================saturday==================================

# import uuid
# from django.contrib.auth.models import AbstractUser
# from django.db import models

# class Permission(models.Model):
#     codename = models.CharField(max_length=100, unique=True)
#     description = models.TextField(blank=True)

#     def __str__(self):
#         return self.codename

# class Role(models.Model):
#     name = models.CharField(max_length=50, unique=True)
#     description = models.TextField(blank=True)
#     permissions = models.ManyToManyField(Permission, blank=True)

#     def __str__(self):
#         return self.name

# class User(AbstractUser):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
#     token_version = models.IntegerField(default=0)

#     def has_permission(self, codename):
#         if not self.role:
#             return False
#         return self.role.permissions.filter(codename=codename).exists()



# =======================================phone Otp =====================================================

# auth_service/models.py
# users/models.py
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta

class Permission(models.Model):
    codename = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.codename

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, blank=True)

    def __str__(self):
        return self.name

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)  # already from AbstractUser
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)  # make unique if you want
    full_name = models.CharField(max_length=100, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    token_version = models.IntegerField(default=0)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []


    def has_permission(self, codename):
        if not self.role:
            return False
        return self.role.permissions.filter(codename=codename).exists()

class OTP(models.Model):
    PURPOSE_CHOICES = [
        ('register', 'Register'),
        ('login', 'Login'),
        ('verify', 'Verify'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=15)
    otp = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default='login')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['phone_number', 'purpose']),
        ]

    def is_expired(self):
        return timezone.now() >= self.expires_at

class StoredRefreshToken(models.Model):
    """
    Opaque refresh tokens stored hashed for rotation and revocation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refresh_tokens')
    token_hash = models.CharField(max_length=128)  # sha256 hex length 64, kept larger
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    user_agent = models.CharField(max_length=256, null=True, blank=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)

    def is_expired(self):
        return timezone.now() >= self.expires_at
