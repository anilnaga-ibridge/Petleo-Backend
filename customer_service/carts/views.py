from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
from customers.models import PetOwnerProfile

class CartViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer

    def get_queryset(self):
        profile = self.request.user
        if not isinstance(profile, PetOwnerProfile):
            profile, _ = PetOwnerProfile.objects.get_or_create(auth_user_id=self.request.user.id)
        
        cart, _ = Cart.objects.get_or_create(owner=profile)
        return Cart.objects.filter(id=cart.id)

    @action(detail=False, methods=['post'], url_path='add-item')
    def add_item(self, request):
        profile = self.request.user
        if not isinstance(profile, PetOwnerProfile):
             return Response({"error": "Profile not found"}, status=403)
             
        cart, _ = Cart.objects.get_or_create(owner=profile)
        
        serializer = CartItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(cart=cart)
            return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['delete'], url_path='remove-item/(?P<item_id>[^/.]+)')
    def remove_item(self, request, item_id=None):
        profile = self.request.user
        CartItem.objects.filter(cart__owner=profile, id=item_id).delete()
        cart, _ = Cart.objects.get_or_create(owner=profile)
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=['post'], url_path='clear')
    def clear(self, request):
        profile = self.request.user
        CartItem.objects.filter(cart__owner=profile).delete()
        return Response({"message": "Cart cleared successfully"})

    @action(detail=False, methods=['post'], url_path='checkout')
    def checkout(self, request):
        """
        Finalize the booking.
        Expects: { "address_id": "...", "notes": "..." }
        """
        print("--- DEBUG: Checkout Triggered ---")
        profile = self.request.user
        cart = Cart.objects.filter(owner=profile).first()
        
        if not cart or not cart.items.exists():
            print("--- DEBUG: Cart is empty ---")
            return Response({"error": "Cart is empty"}, status=400)
            
        items = cart.items.all()
        print(f"--- DEBUG: Found {items.count()} items in cart ---")
        
        # 1. Validation (Capacity, etc.)
        from bookings.services import CapacityService
        
        for item in items:
            if not item.selected_time:
                 return Response({"error": f"Item {item.facility_id} has no time selected"}, status=400)
            
            print(f"--- DEBUG: Checking capacity for {item.facility_id} at {item.selected_time} ---")
            if not CapacityService.check_availability(item.provider_id, item.facility_id, item.selected_time):
                 print("--- DEBUG: Capacity Check Failed ---")
                 return Response({"error": f"Time slot {item.selected_time} is no longer available for facility {item.facility_id}"}, status=400)
        
        from bookings.models import Booking, BookingItem
        from customers.models import PetOwnerAddress
        
        # Get address snapshot
        address_id = request.data.get('address_id')
        address_snapshot = {}
        if address_id:
            try:
                addr = PetOwnerAddress.objects.get(id=address_id, owner=profile)
                address_snapshot = {
                    "line1": addr.address_line1,
                    "city": addr.city,
                    "pincode": addr.pincode
                }
            except PetOwnerAddress.DoesNotExist:
                pass

        # Calculate total (simplistic for now)
        total_price = 0 # In a real app, we'd fetch prices from service_provider_service
        
        try:
            with transaction.atomic():
                print("--- DEBUG: Creating Booking Header ---")
                booking = Booking.objects.create(
                    owner=profile,
                    total_price=0, # Will update after items
                    address_snapshot=address_snapshot,
                    notes=request.data.get('notes', '')
                )
                
                for item in items:
                    # Resolve snapshots
                    import requests
                    resolve_url = f"http://localhost:8002/api/provider/resolve-details/?service_id={item.service_id}&facility_id={item.facility_id}"
                    try:
                        resolve_resp = requests.get(resolve_url, timeout=5)
                        service_snapshot = resolve_resp.json() if resolve_resp.status_code == 200 else {}
                    except Exception:
                        service_snapshot = {}

                    # Employee Assignment
                    # If the user selected a specific doctor (e.g. for Veterinary), use that.
                    # Otherwise, use the auto-assignment logic.
                    if item.employee_id:
                        assigned_employee_id = item.employee_id
                        print(f"--- DEBUG: Using Pre-selected Employee: {assigned_employee_id} ---")
                    else:
                        from bookings.services import AutoAssignmentService
                        print(f"--- DEBUG: Auto-Assigning Employee for Provider {item.provider_id} ---")
                        assigned_employee_id = AutoAssignmentService.assign_employee(
                            item.provider_id, 
                            item.facility_id, 
                            item.selected_time
                        )
                    print(f"--- DEBUG: Final Assigned Employee: {assigned_employee_id} ---")
                    
                    BookingItem.objects.create(
                        booking=booking,
                        provider_id=item.provider_id,
                        assigned_employee_id=assigned_employee_id,
                        pet=item.pet,
                        service_id=item.service_id,
                        facility_id=item.facility_id,
                        selected_time=item.selected_time,
                        service_snapshot=service_snapshot,
                        addons_snapshot=item.selected_addons,
                    )
                
                # Clear cart
                print("--- DEBUG: Usage items.delete() ---")
                items.delete()
                
            print("--- DEBUG: Checkout Success ---")
            return Response({
                "message": "Booking created successfully",
                "booking_id": booking.id
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"--- DEBUG: Checkout Exception: {e} ---")
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)
