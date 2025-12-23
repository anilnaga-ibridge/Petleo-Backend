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
    data = request.data
    plan_id = data["plan_id"]

    # 1. Check if Plan is already Active (Purchased)
    from .models import PurchasedPlan
    if PurchasedPlan.objects.filter(verified_user=verified_user, plan_id=plan_id, is_active=True).exists():
        return Response({"error": "You already have an active subscription for this plan."}, status=400)

    cart, _ = ProviderCart.objects.get_or_create(
        verified_user=verified_user,
        status="active"
    )

    # 2. Check if Plan is already in Cart
    if ProviderCartItem.objects.filter(cart=cart, plan_id=plan_id).exists():
        return Response({"error": "This plan is already in your cart."}, status=400)

    item = ProviderCartItem.objects.create(
        cart=cart,
        plan_id=plan_id,
        billing_cycle_id=data["billing_cycle_id"],
        plan_title=data["plan_title"],
        plan_role=data["plan_role"],
        billing_cycle_name=data["billing_cycle_name"],
        price_amount=data["price_amount"],
        price_currency=data.get("price_currency", "INR"),
        quantity=1,
    )

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
    print("DEBUG: checkout_cart called")
    from .models import PurchasedPlan  # Import local model

    verified_user = get_verified_user(request)

    # Handle multiple active carts (legacy data issue)
    all_active_carts = ProviderCart.objects.filter(
        verified_user=verified_user,
        status="active"
    ).order_by("-created_at")

    if not all_active_carts.exists():
        return Response({"error": "Cart is empty"}, status=400)

    # Find the first cart that has items
    cart_to_use = None
    for c in all_active_carts:
        if c.items.exists():
            cart_to_use = c
            break
    
    # If no cart has items, just use the latest one (it will fail validation below)
    if not cart_to_use:
        cart_to_use = all_active_carts.first()

    # Mark all OTHER active carts as abandoned
    for c in all_active_carts:
        if c.id != cart_to_use.id:
            c.status = "abandoned"
            c.save()
    
    cart = cart_to_use

    if not cart.items.exists():
        return Response({"error": "Cart is empty"}, status=400)

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
                # Assuming Super Admin is on port 8003
                SUPER_ADMIN_URL = "http://127.0.0.1:8003"
                headers = {}
                if "Authorization" in request.headers:
                    headers["Authorization"] = request.headers["Authorization"]
                
                # 1. Notify Super Admin of Purchase (Creates Permissions in Super Admin DB)
                purchase_payload = {
                    "plan_id": str(item.plan_id),
                    "billing_cycle_id": item.billing_cycle_id
                }
                
                with open("checkout_debug.log", "a") as f:
                    f.write(f"Sending purchase request to SA: {purchase_payload}\n")
                    f.write(f"Headers: {headers}\n")

                purchase_response = requests.post(
                    f"{SUPER_ADMIN_URL}/api/superadmin/purchase/",
                    json=purchase_payload,
                    headers=headers
                )
                
                with open("checkout_debug.log", "a") as f:
                    f.write(f"SA Response: {purchase_response.status_code} - {purchase_response.text}\n")

                if purchase_response.status_code != 201:
                    print(f"Super Admin Purchase Failed: {purchase_response.text}")
                
                # We rely on Kafka to sync permissions to ProviderCapabilityAccess
                print("Purchase successful. Waiting for Kafka sync...")

            except Exception as e:
                print(f"Error during checkout sync: {e}")

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
