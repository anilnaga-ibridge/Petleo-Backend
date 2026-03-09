import uuid
from django.db import models
from customers.models import PetOwnerProfile
from pets.models import Pet

class Cart(models.Model):
    """Container for a user's active facility selections"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.OneToOneField(PetOwnerProfile, on_delete=models.CASCADE, related_name='cart')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.owner.user_id}"

class CartItem(models.Model):
    """Detailed selection of a service/facility in the cart"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    
    provider_id = models.UUIDField()
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='cart_items')
    
    service_id = models.CharField(max_length=255)
    facility_id = models.CharField(max_length=255)
    
    selected_time = models.DateTimeField(null=True, blank=True)
    selected_addons = models.JSONField(default=list, blank=True, help_text="List of UUIDs for selected add-ons")
    
    employee_id = models.CharField(max_length=255, null=True, blank=True, help_text="ID of the selected doctor/employee")
    
    price_snapshot = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    provider_auth_id = models.CharField(max_length=255, null=True, blank=True)
    service_snapshot = models.JSONField(default=dict, blank=True)
    
    extra_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"CartItem {self.facility_id} in {self.cart.id}"
