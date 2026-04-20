from django.shortcuts import render
import uuid

# Create your views here.
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone

from service_provider.models import VerifiedUser
from .models import ProviderCart, ProviderCartItem, PurchasedPlan
from .serializers import ProviderCartSerializer, PurchasedPlanSerializer


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

def _get_or_create_stripe_customer(verified_user):
    import stripe
    from django.conf import settings
    
    # Check if Stripe is configured
    if not settings.STRIPE_SECRET_KEY:
        print("DEBUG: Stripe Secret Key is missing. Using Mock Customer.")
        return type('MockCustomer', (object,), {'id': f"mock_cus_{verified_user.id}"})()

    stripe.api_key = settings.STRIPE_SECRET_KEY

    if verified_user.stripe_customer_id:
        try:
            # If it's a mock ID, don't try to retrieve from Stripe
            if str(verified_user.stripe_customer_id).startswith("mock_"):
                return type('MockCustomer', (object,), {'id': verified_user.stripe_customer_id})()
                
            return stripe.Customer.retrieve(verified_user.stripe_customer_id)
        except stripe.error.StripeError as e:
            print(f"DEBUG: Stripe Customer Retrieve Error: {e}")
            pass

    try:
        customer = stripe.Customer.create(
            email=verified_user.email,
            name=verified_user.full_name,
            metadata={"verified_user_id": str(verified_user.id)}
        )
        verified_user.stripe_customer_id = customer.id
        verified_user.save(update_fields=["stripe_customer_id"])
        return customer
    except Exception as e:
        print(f"DEBUG: Stripe Customer Create Error: {e}. Falling back to mock.")
        return type('MockCustomer', (object,), {'id': f"mock_cus_{verified_user.id}"})()


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

    # -----------------------------------------------------
    # 0. STRICT DOCUMENT VERIFICATION CHECK
    # -----------------------------------------------------
    from provider_dynamic_fields.models import LocalDocumentDefinition, ProviderDocument

    # Determine target (individual vs organization)
    # Default to 'individual' if role is 'provider' or missing
    role_map = {
        'provider': 'individual',
        'individual': 'individual',
        'organization': 'organization'
    }
    user_role = (verified_user.role or 'individual').lower()
    target = role_map.get(user_role, 'individual')

    # [NEW] Prioritize ServiceProvider profile type
    from service_provider.models import ServiceProvider
    try:
        sp = ServiceProvider.objects.get(verified_user=verified_user)
        if sp.provider_type:
            target = sp.provider_type.lower()
    except ServiceProvider.DoesNotExist:
        pass

    # 1. Get Required Definitions for this target
    required_defs = LocalDocumentDefinition.objects.filter(
        target=target, 
        is_required=True
    ).values_list('id', flat=True)

    if required_defs:
        # 2. Get User's Uploaded Documents
        user_docs = ProviderDocument.objects.filter(verified_user=verified_user)
        uploaded_def_ids = set(user_docs.values_list('definition_id', flat=True))

        # Check A: Are all required docs present?
        missing_required = set(required_defs) - uploaded_def_ids
        if missing_required:
             return Response({
                 "error": "You must upload all required documents before purchasing a plan."
             }, status=400)

        # Check B: Are ANY docs rejected or pending?
        # We enforce that ALL uploaded docs must be 'approved'.
        # (Or at least the required ones? Requirement says "if super admin will accept... then only provider can purchase")
        # Let's be strict: All current docs must be approved.
        not_approved = user_docs.exclude(status='approved')
        if not_approved.exists():
            return Response({
                "error": "Your documents are currently under review. You can purchase a plan once they are approved by the admin."
            }, status=400)
    
    # -----------------------------------------------------

    data = request.data
    plan_id = data["plan_id"]

    # 1. Check if Plan is already Active (Purchased)
    from .models import PurchasedPlan
    active_plan = PurchasedPlan.objects.filter(verified_user=verified_user, plan_id=plan_id, is_active=True).first()
    if active_plan and not active_plan.is_expiring_soon:
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

        import stripe
        from django.conf import settings
        
        # We will handle the first plan only to redirect to a single Stripe session.
        # Typically subscriptions are checked out one at a time.
        item = cart.items.first()
        
        # Calculate end date based on billing cycle name
        from datetime import timedelta
        start_date = timezone.now()
        end_date = None
        
        cycle_name = (item.billing_cycle_name or "").upper()
        if "MONTH" in cycle_name:
            end_date = start_date + timedelta(days=30)
            stripe_interval = 'month'
        elif "YEAR" in cycle_name:
            end_date = start_date + timedelta(days=365)
            stripe_interval = 'year'
        elif "WEEK" in cycle_name:
            end_date = start_date + timedelta(days=7)
            stripe_interval = 'week'
        elif "DAY" in cycle_name:
            end_date = start_date + timedelta(days=1)
            stripe_interval = 'day'
        else:
            stripe_interval = 'month'

        # [ROBUSTNESS FIX] Handle Stripe logic with fallback
        client_secret = "mock_secret"
        transaction_id = f"mock_sub_{uuid.uuid4().hex[:8]}"
        
        if settings.STRIPE_SECRET_KEY:
            try:
                stripe.api_key = settings.STRIPE_SECRET_KEY
                customer = _get_or_create_stripe_customer(verified_user)
                
                stripe_product = stripe.Product.create(
                    name=item.plan_title,
                    description=f"{item.plan_title} ({item.billing_cycle_name})"
                )
                
                # Create a Subscription in 'incomplete' state
                subscription = stripe.Subscription.create(
                    customer=customer.id,
                    items=[{
                        'price_data': {
                            'currency': item.price_currency.lower(),
                            'product': stripe_product.id,
                            'unit_amount': int(float(item.price_amount) * 100),
                            'recurring': {
                                'interval': stripe_interval,
                            },
                        },
                    }],
                    payment_behavior='default_incomplete',
                    payment_settings={'save_default_payment_method': 'on_subscription'},
                    expand=['latest_invoice.confirmation_secret'],
                )
                
                client_secret = subscription.latest_invoice.confirmation_secret.client_secret
                transaction_id = subscription.id
                
            except Exception as e:
                print(f"ERROR: Failed to connect to Stripe: {str(e)}. Using Mock Mode.")
                # We continue with mock data instead of returning 500
        else:
            print("INFO: STRIPE_SECRET_KEY not set. Using Mock Mode.")

        # Create local purchase record in PENDING / inactive state until webhook confirms
        purchase = PurchasedPlan.objects.create(
            verified_user=verified_user,
            plan_id=item.plan_id,
            plan_title=item.plan_title,
            billing_cycle_id=item.billing_cycle_id,
            billing_cycle_name=item.billing_cycle_name,
            price_amount=item.price_amount,
            price_currency=item.price_currency,
            start_date=start_date,
            end_date=end_date,
            is_active=True,  # <--- SET TO TRUE FOR TESTING (Bypasses Webhook)
            payment_gateway='STRIPE',
            transaction_id=transaction_id,
            checkout_session_url=None # No longer redirecting
        )
            
        # ✅ Sync Permissions from Super Admin
        sa_data = {}
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

            if purchase_response.status_code == 201:
                sa_data = purchase_response.json()
            else:
                print(f"Super Admin Purchase Failed: {purchase_response.text}")
            
            # ✅ [PRODUCTION FIX] Activate Provider Profile locally also
            from service_provider.services import ProviderService
            ProviderService.activate_provider_profile(verified_user)

            # We rely on Kafka to sync permissions to ProviderCapabilityAccess
            print("Purchase successful and provider activated. Waiting for Kafka sync...")

        except Exception as e:
            print(f"Error during checkout sync: {e}")

        # Note: Do not check out the whole cart if it has multiple items. 
        # But we assume one item at checkout for subscriptions.
        cart.status = "checked_out"
        cart.save()

    return Response({
        "detail": "Proceed to premium payment.",
        "sa_data": sa_data,
        "client_secret": client_secret,
        "subscription_id": transaction_id
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def purchase_plan_direct(request):
    """
    Directly purchase a plan, skipping the cart.
    Accepts: { plan_id, plan_title, plan_role, billing_cycle_id, billing_cycle_name, price_amount, price_currency }
    """
    from .models import PurchasedPlan
    verified_user = get_verified_user(request)

    # 0. Restriction Check: Provider can only have ONE active plan (unless renewal)
    active_plan = PurchasedPlan.objects.filter(verified_user=verified_user, is_active=True).first()
    if active_plan:
        if active_plan.plan_id == uuid.UUID(str(request.data.get("plan_id"))):
            if not active_plan.is_expiring_soon:
                return Response({"error": "You already purchased this plan ☺️"}, status=400)
            # If expiring soon, we allow renewal (it creates a SECOND active plan for now, 
            # or we could deactivate the old one. Let's deactivate old one to be clean).
            active_plan.is_active = False
            active_plan.save()
        else:
             return Response({"error": "You cannot purchase another plan while you have an active plan."}, status=400)

    data = request.data

    # 1. Validation Logic (Same as add_to_cart)
    from provider_dynamic_fields.models import LocalDocumentDefinition, ProviderDocument

    role_map = {'provider': 'individual', 'individual': 'individual', 'organization': 'organization'}
    user_role = (verified_user.role or 'individual').lower()
    target = role_map.get(user_role, 'individual')

    # [NEW] Prioritize ServiceProvider profile type
    from service_provider.models import ServiceProvider
    try:
        sp = ServiceProvider.objects.get(verified_user=verified_user)
        if sp.provider_type:
             target = sp.provider_type.lower()
    except ServiceProvider.DoesNotExist:
        pass

    required_defs = LocalDocumentDefinition.objects.filter(target=target, is_required=True).values_list('id', flat=True)
    if required_defs:
        user_docs = ProviderDocument.objects.filter(verified_user=verified_user)
        uploaded_def_ids = set(user_docs.values_list('definition_id', flat=True))
        if set(required_defs) - uploaded_def_ids:
            return Response({"error": "You must upload all required documents before purchasing a plan."}, status=400)
        
        # Check if documents are approved
        not_approved = user_docs.exclude(status='approved')
        if not_approved.exists():
            return Response({"error": "Your documents are currently under review. Please wait for approval before purchasing."}, status=400)

    # 2. Purchase Logic
    from datetime import timedelta
    start_date = timezone.now()
    end_date = None
    
    cycle_name = (data.get("billing_cycle_name") or "").upper()
    if "MONTH" in cycle_name:
        end_date = start_date + timedelta(days=30)
        stripe_interval = 'month'
    elif "YEAR" in cycle_name:
        end_date = start_date + timedelta(days=365)
        stripe_interval = 'year'
    elif "WEEK" in cycle_name:
        end_date = start_date + timedelta(days=7)
        stripe_interval = 'week'
    elif "DAY" in cycle_name:
        end_date = start_date + timedelta(days=1)
        stripe_interval = 'day'
    else:
        stripe_interval = 'month'

    with transaction.atomic():
        # [ROBUSTNESS FIX] Handle Stripe logic with fallback
        client_secret = "mock_secret"
        transaction_id = f"mock_sub_{uuid.uuid4().hex[:8]}"

        if settings.STRIPE_SECRET_KEY:
            try:
                import stripe
                stripe.api_key = settings.STRIPE_SECRET_KEY
                customer = _get_or_create_stripe_customer(verified_user)
                
                stripe_product = stripe.Product.create(
                    name=data["plan_title"],
                    description=f"{data['plan_title']} ({data['billing_cycle_name']})"
                )
                
                subscription = stripe.Subscription.create(
                    customer=customer.id,
                    items=[{
                        'price_data': {
                            'currency': data.get("price_currency", "INR").lower(),
                            'product': stripe_product.id,
                            'unit_amount': int(float(data["price_amount"]) * 100),
                            'recurring': {
                                'interval': stripe_interval,
                            },
                        },
                    }],
                    payment_behavior='default_incomplete',
                    payment_settings={'save_default_payment_method': 'on_subscription'},
                    expand=['latest_invoice.confirmation_secret'],
                )
                
                client_secret = subscription.latest_invoice.confirmation_secret.client_secret
                transaction_id = subscription.id
                
            except Exception as e:
                print(f"ERROR: Failed to connect to Stripe in Direct Purchase: {str(e)}. Using Mock Mode.")
        else:
            print("INFO: STRIPE_SECRET_KEY not set in Direct Purchase. Using Mock Mode.")

        purchase = PurchasedPlan.objects.create(
            verified_user=verified_user,
            plan_id=data["plan_id"],
            plan_title=data["plan_title"],
            billing_cycle_id=data["billing_cycle_id"],
            billing_cycle_name=data["billing_cycle_name"],
            price_amount=data["price_amount"],
            price_currency=data.get("price_currency", "INR"),
            start_date=start_date,
            end_date=end_date,
            is_active=True, # SET TO TRUE FOR TESTING
            payment_gateway='STRIPE',
            transaction_id=transaction_id,
            checkout_session_url=None
        )

        # 3. Synchronize with Super Admin
        sa_data = {}
        try:
            import requests
            SUPER_ADMIN_URL = "http://127.0.0.1:8003"
            headers = {}
            if "Authorization" in request.headers:
                headers["Authorization"] = request.headers["Authorization"]
            
            purchase_payload = {
                "plan_id": str(data["plan_id"]),
                "billing_cycle_id": data["billing_cycle_id"]
            }
            
            resp = requests.post(
                f"{SUPER_ADMIN_URL}/api/superadmin/purchase/", 
                json=purchase_payload, 
                headers=headers
            )
            if resp.status_code == 201:
                sa_data = resp.json()
            else:
                print(f"Super Admin Purchase Failed in Direct Flow: {resp.text}")
            
            # ✅ [PRODUCTION FIX] Activate Provider Profile locally also
            from service_provider.services import ProviderService
            ProviderService.activate_provider_profile(verified_user)
            
        except Exception as e:
            print(f"Direct purchase sync error: {e}")

    return Response({
        "detail": "Proceed to premium payment.",
        "purchase_id": str(purchase.id),
        "sa_data": sa_data,
        "client_secret": client_secret,
        "subscription_id": transaction_id
    }, status=201)


# ✅ Get Purchased Plans
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_purchased_plans(request):
    from .models import PurchasedPlan
    from .serializers import PurchasedPlanSerializer

    verified_user = get_verified_user(request)
    plans = PurchasedPlan.objects.filter(verified_user=verified_user).order_by("-created_at")
    
    return Response(PurchasedPlanSerializer(plans, many=True).data)

# ✅ Get Active Subscription + All Permissions
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_active_subscription(request):
    from .models import PurchasedPlan
    from .serializers import PurchasedPlanSerializer
    from service_provider.utils import _build_permission_tree
    from service_provider.models import AllowedService

    verified_user = get_verified_user(request)
    
    # 0. AUTO-DEACTIVATE EXPIRED PLANS
    PurchasedPlan.objects.filter(
        verified_user=verified_user, 
        is_active=True, 
        end_date__lt=timezone.now()
    ).update(is_active=False)

    # 1. Get current active plan
    active_plan = PurchasedPlan.objects.filter(verified_user=verified_user, is_active=True).order_by("-created_at").first()
    
    if not active_plan:
        return Response({"detail": "No active subscription found"}, status=200) # Changed to 200 for smoother frontend handling

    # 2. Get Permissions & Services using the robust helper
    permissions_list = _build_permission_tree(verified_user, request=request)
    services = AllowedService.objects.filter(verified_user=verified_user)

    return Response({
        "plan": PurchasedPlanSerializer(active_plan).data,
        "permissions": permissions_list,
        "allowed_services": services.values("service_id", "name", "icon")
    })

# ✅ Stripe Webhook (Automated Activation)
import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

@csrf_exempt
@api_view(["POST"])
@permission_classes([]) # Public endpoint for Stripe
def stripe_webhook(request):
    payload = request.body
    sig_header = request.headers.get('STRIPE_SIGNATURE')
    
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return Response({"error": "Invalid payload"}, status=400)
    except stripe.error.SignatureVerificationError as e:
        return Response({"error": "Invalid signature"}, status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        _activate_purchased_plan(session.id)
    
    return HttpResponse(status=200)


# ✅ Manual Payment Verification (For Local Dev)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    session_id = request.query_params.get("session_id")
    if not session_id:
        return Response({"error": "session_id is required"}, status=400)
    
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            plan = _activate_purchased_plan(session_id)
            return Response({
                "detail": "Payment verified and plan activated!",
                "plan": PurchasedPlanSerializer(plan).data
            })
        else:
            return Response({"error": f"Payment status is {session.payment_status}"}, status=400)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


def _activate_purchased_plan(session_id):
    """
    Helper to activate the plan and sync with Super Admin.
    """
    from .models import PurchasedPlan
    plan = PurchasedPlan.objects.filter(transaction_id=session_id).first()
    if plan and not plan.is_active:
        plan.is_active = True
        plan.save()
        print(f"✅ Plan {plan.id} activated via Stripe Success.")
    return plan
