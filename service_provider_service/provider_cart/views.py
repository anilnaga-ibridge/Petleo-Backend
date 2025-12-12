from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone

from service_provider.models import VerifiedUser
from .models import ProviderCart, ProviderCartItem
from .serializers import ProviderCartSerializer


# ✅ Helper
# ✅ Helper
def get_verified_user(request):
    user = request.user
    # print(f"DEBUG: get_verified_user request.user type: {type(user)}")
    
    # 1. If user is VerifiedUser instance
    if isinstance(user, VerifiedUser):
        return user

    # 2. If user is an object with auth_user_id (e.g. some custom user model)
    if hasattr(user, 'auth_user_id'):
        return get_object_or_404(VerifiedUser, auth_user_id=user.auth_user_id)

    # 3. If user is an object with id (e.g. Django User or SimpleObject)
    # We assume this ID is the Auth Service ID
    if hasattr(user, 'id'):
        return get_object_or_404(VerifiedUser, auth_user_id=user.id)
        
    # 4. If user is a dict (raw JWT payload)
    if isinstance(user, dict):
        auth_id = user.get('auth_user_id') or user.get('id') or user.get('user_id')
        return get_object_or_404(VerifiedUser, auth_user_id=auth_id)

    # Fallback or Error
    raise ValueError(f"Cannot resolve VerifiedUser from request.user: {type(user)}")


# ✅ Get Active Cart
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_my_cart(request):
    verified_user = get_verified_user(request)

    cart, created = ProviderCart.objects.get_or_create(
        verified_user=verified_user,
        status="active"
    )

    return Response(ProviderCartSerializer(cart).data)


# ✅ Add Plan To Cart
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    verified_user = get_verified_user(request)

    cart, _ = ProviderCart.objects.get_or_create(
        verified_user=verified_user,
        status="active"
    )

    data = request.data

    item, created = ProviderCartItem.objects.get_or_create(
        cart=cart,
        plan_id=data["plan_id"],
        billing_cycle_id=data["billing_cycle_id"],
        defaults={
            "plan_title": data["plan_title"],
            "plan_role": data["plan_role"],
            "billing_cycle_name": data["billing_cycle_name"],
            "price_amount": data["price_amount"],
            "price_currency": data.get("price_currency", "INR"),
            "quantity": 1,
        }
    )

    if not created:
        item.quantity += 1
        item.save()

    return Response({"detail": "Plan added to cart"})


# ✅ Remove Item From Cart
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def remove_from_cart(request, item_id):
    verified_user = get_verified_user(request)

    cart = get_object_or_404(
        ProviderCart,
        verified_user=verified_user,
        status="active"
    )

    item = get_object_or_404(ProviderCartItem, id=item_id, cart=cart)
    item.delete()

    return Response({"detail": "Item removed"})


# ✅ Checkout (Convert Cart → Purchased Plans)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def checkout_cart(request):
    from .models import PurchasedPlan  # Import local model

    verified_user = get_verified_user(request)

    cart = get_object_or_404(
        ProviderCart,
        verified_user=verified_user,
        status="active"
    )

    with transaction.atomic():

        for item in cart.items.all():
            # Create local purchase record
            PurchasedPlan.objects.create(
                verified_user=verified_user,
                plan_id=item.plan_id,
                plan_title=item.plan_title,
                billing_cycle_id=item.billing_cycle_id,
                billing_cycle_name=item.billing_cycle_name,
                price_amount=item.price_amount,
                price_currency=item.price_currency,
                start_date=timezone.now(),
                is_active=True
            )
            
            # ✅ Sync Permissions from Super Admin
            try:
                import requests
                from service_provider.models import ProviderPermission, AllowedService
                
                # Assuming Super Admin is on port 8003
                SUPER_ADMIN_URL = "http://127.0.0.1:8003"
                response = requests.get(f"{SUPER_ADMIN_URL}/api/superadmin/plans/{item.plan_id}/permissions/")
                
                if response.status_code == 200:
                    data = response.json()
                    perms = data.get("permissions", [])
                    services = data.get("services", [])
                    
                    # Sync Permissions
                    for code in perms:
                        ProviderPermission.objects.get_or_create(
                            verified_user=verified_user,
                            permission_code=code
                        )
                        
                    # Sync Allowed Services
                    for svc in services:
                        AllowedService.objects.update_or_create(
                            verified_user=verified_user,
                            service_id=svc["id"],
                            defaults={
                                "name": svc["name"],
                                "icon": svc["icon"]
                            }
                        )
                else:
                    print(f"Failed to fetch permissions for plan {item.plan_id}: {response.status_code}")
            except Exception as e:
                print(f"Error syncing permissions: {e}")

        cart.status = "checked_out"
        cart.save()

    return Response({"detail": "Payment successful. Plans activated."})


# ✅ Get Purchased Plans
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_purchased_plans(request):
    from .models import PurchasedPlan
    from .serializers import PurchasedPlanSerializer

    verified_user = get_verified_user(request)
    plans = PurchasedPlan.objects.filter(verified_user=verified_user).order_by("-created_at")
    
    return Response(PurchasedPlanSerializer(plans, many=True).data)
