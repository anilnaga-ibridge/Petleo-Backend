from django.db import models

class DocumentDefinition(models.Model):
    ROLE_CHOICES = [
        ("individual", "Individual"),
        ("organization", "Organization"),
        ("both", "Both"),
    ]

    FIELD_TYPE_CHOICES = [
        ("file", "File"),
        ("text", "Text"),
        ("number", "Number"),
        ("date", "Date"),
    ]

    code = models.CharField(max_length=100, unique=True)  # e.g. "aadhar_card"
    label = models.CharField(max_length=255)              # "Aadhar Card"
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES, default="file")
    required = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} ({self.role})"
