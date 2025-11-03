from django.db import models
from django.utils.text import slugify
import random
import string

class PetType(models.Model):
    id = models.TextField(primary_key=True, max_length=50, editable=False)
    name = models.CharField(max_length=255, null=True, blank=False)
    key = models.CharField(default='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_custom_id(self):
        while True:
            slug = slugify(self.name)
            rand = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
            custom_id = f"{slug}_{rand}"
            if not PetType.objects.filter(id=custom_id).exists():
                return custom_id

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = self.generate_custom_id()
        if not self.key:
            self.key = slugify(self.name).replace("-", "_")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class PetBreed(models.Model):
    id = models.TextField(primary_key=True, max_length=50, editable=False)
    petType = models.ForeignKey(PetType, on_delete=models.CASCADE, related_name="breeds")
    breed = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_custom_id(self):
        base_slug = slugify(self.breed) if self.breed else "breed"
        rand = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        max_slug_length = 50 - len(rand) - 1
        base_slug = base_slug[:max_slug_length]
        custom_id = f"{base_slug}_{rand}"
        while PetBreed.objects.filter(id=custom_id).exists():
            rand = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
            custom_id = f"{base_slug}_{rand}"
        return custom_id

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = self.generate_custom_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.breed
