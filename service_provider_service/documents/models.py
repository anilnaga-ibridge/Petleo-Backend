from django.db import models

class Provider(models.Model):
    ROLE_CHOICES = [
        ("individual", "Individual"),
        ("organization", "Organization"),
    ]
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.role})"

class ProviderDocumentSubmission(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="submissions")
    code = models.CharField(max_length=100)  # matches DocumentDefinition.code from SuperAdmin
    # If field_type=file -> store file. If text -> value stored here.
    file = models.FileField(upload_to="provider_docs/", null=True, blank=True)
    value = models.TextField(blank=True, null=True)
    required = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    remarks = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("provider", "code")  # one submission per provider+code

    def __str__(self):
        return f"{self.provider} - {self.code} ({self.status})"
