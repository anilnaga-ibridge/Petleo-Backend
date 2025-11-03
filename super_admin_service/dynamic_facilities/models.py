from django.db import models
from dynamic_services.models import Service
from django.utils.text import slugify

class Facility(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="facilities")
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.value:
            self.value = slugify(self.name).replace("-", "_")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.service.display_name})"
