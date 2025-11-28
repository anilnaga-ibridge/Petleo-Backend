# # super_admin/models.py
# import uuid
# from django.db import models
# from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
# from django.utils import timezone

# STATUS_CHOICES = [
#     ('active', 'Active'),
#     ('pending', 'Pending'),
#     ('in_active', 'In Active'),
#     ('blocked', 'Blocked'),
# ]

# class SuperAdminManager(BaseUserManager):
#     def create_superadmin(self, email, contact, password=None):
#         if not email:
#             raise ValueError("SuperAdmins must have an email address")
#         if not contact:
#             raise ValueError("SuperAdmins must have a contact number")

#         superadmin = self.model(
#             email=self.normalize_email(email),
#             contact=contact
#         )
#         superadmin.set_password(password)
#         superadmin.save(using=self._db)
#         return superadmin

# class SuperAdmin(AbstractBaseUser):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#    # models.py
#     auth_user_id = models.CharField(max_length=50, unique=True ,null=True)
#   # Link to Auth Service user ID
#     email = models.EmailField(max_length=255, unique=True)
#     contact = models.CharField(max_length=15, blank=True, null=True, unique=False)
#     first_name = models.CharField(max_length=30, blank=True)
#     last_name = models.CharField(max_length=30, blank=True)
#     is_active = models.BooleanField(default=True)
#     is_staff = models.BooleanField(default=True)
#     is_admin = models.BooleanField(default=True)
#     user_role = models.CharField(max_length=50, default='Admin',null=True)
#     is_super_admin = models.BooleanField(default=True)
#     activity_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_active')

#     objects = SuperAdminManager()

#     USERNAME_FIELD = 'email'
#     REQUIRED_FIELDS = ['contact']

#     def __str__(self):
#         return self.email





# class VerifiedUser(models.Model):
#     """
#     Stores verified users coming from the Auth Service (via Kafka).
#     Each service can extend this model as per its domain.
#     """
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     auth_user_id = models.UUIDField(unique=True)  # Link to Auth Service user
#     full_name = models.CharField(max_length=100, blank=True, null=True)
#     email = models.EmailField(blank=True, null=True)
#     phone_number = models.CharField(max_length=15, blank=True, null=True)
#     role = models.CharField(max_length=50, blank=True, null=True)
#     permissions = models.JSONField(default=list, blank=True)
#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = "verified_users"
#         indexes = [
#             models.Index(fields=["auth_user_id"]),
#             models.Index(fields=["email"]),
#             models.Index(fields=["phone_number"]),
#         ]

#     def __str__(self):
#         return f"{self.full_name or 'Unknown'} ({self.role})"
    
    
    
# # ✅ Active only manager (filters soft-deleted)
# class ActiveAdminProfileManager(models.Manager):
#     def get_queryset(self):
#         return super().get_queryset().filter(is_deleted=False)
    
# class Permission(models.Model):
#     """
#     Stores a permission that SuperAdmin can assign to Admins.
#     """
#     code = models.CharField(max_length=100, unique=True)
#     name = models.CharField(max_length=150)
#     description = models.TextField(blank=True, null=True)

#     class Meta:
#         db_table = "permissions"

#     def __str__(self):
#         return self.name


# # class AdminProfile(models.Model):
# #     """
# #     Admin profile extending VerifiedUser with additional info.
# #     """
# #     verified_user = models.OneToOneField(
# #         VerifiedUser, on_delete=models.CASCADE, related_name="admin_profile"
# #     )
# #     department = models.CharField(max_length=100, blank=True, null=True)
# #     designation = models.CharField(max_length=100, blank=True, null=True)
# #     address = models.TextField(blank=True, null=True)
# #     profile_image = models.ImageField(upload_to="admin_profiles/", blank=True, null=True)
    
# #     # soft delete and activity tracking
# #     is_deleted = models.BooleanField(default=False)
# #     activity_status = models.CharField(
# #         max_length=20,
# #         choices=[
# #             ("active", "Active"),
# #             ("inactive", "Inactive"),
# #             ("suspended", "Suspended"),
# #         ],
# #         default="active",
# #     )

# #     permissions = models.ManyToManyField(Permission, blank=True, related_name="admins")

# #     created_at = models.DateTimeField(auto_now_add=True)
# #     updated_at = models.DateTimeField(auto_now=True)

# #     # managers
# #     objects = ActiveAdminProfileManager()
# #     all_objects = models.Manager()

# #     class Meta:
# #         db_table = "admin_profiles"

# #     def __str__(self):
# #         return f"Admin: {self.verified_user.full_name or self.verified_user.email}"


# class AdminProfile(models.Model):
#     """
#     Admin profile extending VerifiedUser with additional info.
#     """
#     verified_user = models.OneToOneField(
#         VerifiedUser,
#         on_delete=models.CASCADE,
#         related_name="admin_profile",
#         to_field="auth_user_id",  # 👈 This makes FK use auth_user_id instead of id
#         db_column="verified_user_auth_id"  # Optional, for clarity in DB
#     )
#     department = models.CharField(max_length=100, blank=True, null=True)
#     designation = models.CharField(max_length=100, blank=True, null=True)
#     address = models.TextField(blank=True, null=True)
#     profile_image = models.ImageField(upload_to="admin_profiles/", blank=True, null=True)
    
#     # soft delete and activity tracking
#     is_deleted = models.BooleanField(default=False)
#     activity_status = models.CharField(
#         max_length=20,
#         choices=[
#             ("active", "Active"),
#             ("inactive", "Inactive"),
#             ("suspended", "Suspended"),
#         ],
#         default="active",
#     )

#     permissions = models.ManyToManyField(Permission, blank=True, related_name="admins")

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     objects = ActiveAdminProfileManager()
#     all_objects = models.Manager()

#     class Meta:
#         db_table = "admin_profiles"

#     def __str__(self):
#         return f"Admin: {self.verified_user.email}"




# # super_admin/models.py
# import uuid
# from django.db import models
# from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
# from django.utils import timezone

# STATUS_CHOICES = [
#     ('active', 'Active'),
#     ('pending', 'Pending'),
#     ('inactive', 'Inactive'),
#     ('blocked', 'Blocked'),
# ]

# class SuperAdminManager(BaseUserManager):
#     def create_superadmin(self, email, contact, password=None):
#         if not email:
#             raise ValueError("SuperAdmins must have an email address")
#         if not contact:
#             raise ValueError("SuperAdmins must have a contact number")

#         superadmin = self.model(
#             email=self.normalize_email(email),
#             contact=contact
#         )
#         superadmin.set_password(password)
#         superadmin.save(using=self._db)
#         return superadmin

# class SuperAdmin(AbstractBaseUser):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     auth_user_id = models.UUIDField(unique=True, null=True, blank=True)  # link to Auth Service
#     email = models.EmailField(max_length=255, unique=True)
#     contact = models.CharField(max_length=15, blank=True, null=True)
#     first_name = models.CharField(max_length=30, blank=True)
#     last_name = models.CharField(max_length=30, blank=True)
#     is_active = models.BooleanField(default=True)
#     is_staff = models.BooleanField(default=True)
#     is_admin = models.BooleanField(default=True)
#     user_role = models.CharField(max_length=50, default='Admin', null=True)
#     is_super_admin = models.BooleanField(default=True)
#     activity_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='inactive')

#     objects = SuperAdminManager()

#     USERNAME_FIELD = 'email'
#     REQUIRED_FIELDS = ['contact']

#     def __str__(self):
#         return self.email


# class VerifiedUser(models.Model):
#     """
#     Stores verified users coming from the Auth Service (via Kafka).
#     auth_user_id is the canonical id from Auth service (UUID).
#     """
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     auth_user_id = models.UUIDField(unique=True)  # Link to Auth Service user
#     full_name = models.CharField(max_length=100, blank=True, null=True)
#     email = models.EmailField(blank=True, null=True)
#     phone_number = models.CharField(max_length=15, blank=True, null=True)
#     role = models.CharField(max_length=50, blank=True, null=True)
#     # permissions stored at service-level may be a list - but we will have Permission model for assignments
#     permissions = models.JSONField(default=list, blank=True)
#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = "verified_users"
#         indexes = [
#             models.Index(fields=["auth_user_id"]),
#             models.Index(fields=["email"]),
#             models.Index(fields=["phone_number"]),
#         ]

#     def __str__(self):
#         return f"{self.full_name or 'Unknown'} ({self.role})"


# class ActiveAdminProfileManager(models.Manager):
#     def get_queryset(self):
#         return super().get_queryset().filter(is_deleted=False)


# class Permission(models.Model):
#     """
#     Stores a permission that SuperAdmin can assign to Admins.
#     """
#     code = models.CharField(max_length=100, unique=True)
#     name = models.CharField(max_length=150)
#     description = models.TextField(blank=True, null=True)

#     class Meta:
#         db_table = "permissions"

#     def __str__(self):
#         return self.name


# class AdminProfile(models.Model):
#     """
#     Admin profile extending VerifiedUser with additional info.
#     The relation uses verified_user.auth_user_id so all lookups use auth_user_id.
#     """
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     verified_user = models.OneToOneField(
#         VerifiedUser,
#         on_delete=models.CASCADE,
#         related_name="admin_profile",
#         to_field="auth_user_id",  # FK refers to VerifiedUser.auth_user_id
#         db_column="verified_user_auth_id"
#     )
#     department = models.CharField(max_length=100, blank=True, null=True)
#     designation = models.CharField(max_length=100, blank=True, null=True)
#     address = models.TextField(blank=True, null=True)
#     profile_image = models.ImageField(upload_to="admin_profiles/", blank=True, null=True)

#     is_deleted = models.BooleanField(default=False)
#     activity_status = models.CharField(
#         max_length=20,
#         choices=[
#             ("active", "Active"),
#             ("inactive", "Inactive"),
#             ("suspended", "Suspended"),
#         ],
#         default="active",
#     )

#     permissions = models.ManyToManyField(Permission, blank=True, related_name="admins")

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     # managers
#     objects = ActiveAdminProfileManager()
#     all_objects = models.Manager()

#     class Meta:
#         db_table = "admin_profiles"

#     def __str__(self):
#         return f"Admin: {self.verified_user.email}"



# super_admin/models.py
import uuid
from django.db import models
from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.utils import timezone

STATUS_CHOICES = [
    ('active', 'Active'),
    ('pending', 'Pending'),
    ('inactive', 'Inactive'),
    ('blocked', 'Blocked'),
]

class SuperAdminManager(BaseUserManager):
    def create_superadmin(self, email, contact, password=None):
        if not email:
            raise ValueError("SuperAdmins must have an email address")
        if not contact:
            raise ValueError("SuperAdmins must have a contact number")

        superadmin = self.model(
            email=self.normalize_email(email),
            contact=contact
        )
        superadmin.set_password(password)
        superadmin.save(using=self._db)
        return superadmin


class SuperAdmin(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # FIXED 👇 (UUIDField → CharField)
    auth_user_id = models.CharField(max_length=50, unique=True, null=True, blank=True)

    email = models.EmailField(max_length=255, unique=True)
    contact = models.CharField(max_length=15, blank=True, null=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=True)
    user_role = models.CharField(max_length=50, default='Admin', null=True)
    is_super_admin = models.BooleanField(default=True)

    activity_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='inactive'
    )

    objects = SuperAdminManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['contact']

    def __str__(self):
        return self.email



class VerifiedUser(models.Model):
    """
    Stores verified users coming from the Auth Service (via Kafka).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # FIXED 👇 (UUIDField → CharField)
    auth_user_id = models.CharField(max_length=50, unique=True)

    full_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    role = models.CharField(max_length=50, blank=True, null=True)
    permissions = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "verified_users"
        indexes = [
            models.Index(fields=["auth_user_id"]),
            models.Index(fields=["email"]),
            models.Index(fields=["phone_number"]),
        ]

    def __str__(self):
        return f"{self.full_name or 'Unknown'} ({self.role})"



class ActiveAdminProfileManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Permission(models.Model):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "permissions"

    def __str__(self):
        return self.name



class AdminProfile(models.Model):
    """
    Admin profile extending VerifiedUser with additional info.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # FIXED: VerifiedUser.auth_user_id is CharField now
    verified_user = models.OneToOneField(
        VerifiedUser,
        on_delete=models.CASCADE,
        related_name="admin_profile",
        to_field="auth_user_id",       # FK uses CharField auth_user_id
        db_column="verified_user_auth_id"
    )

    department = models.CharField(max_length=100, blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(upload_to="admin_profiles/", blank=True, null=True)

    is_deleted = models.BooleanField(default=False)

    activity_status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("inactive", "Inactive"),
            ("suspended", "Suspended"),
        ],
        default="active",
    )

    permissions = models.ManyToManyField(Permission, blank=True, related_name="admins")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActiveAdminProfileManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "admin_profiles"

    def __str__(self):
        return f"Admin: {self.verified_user.email}"
