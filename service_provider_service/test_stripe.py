import stripe
from service_provider_service.settings import STRIPE_SECRET_KEY
stripe.api_key = STRIPE_SECRET_KEY

# let's create a customer and a subscription to see the shape
customer = stripe.Customer.create(email="test_sub@example.com")
product = stripe.Product.create(name="Test")
sub = stripe.Subscription.create(
    customer=customer.id,
    items=[{'price_data': {'currency': 'inr', 'unit_amount': 1000, 'product': product.id, 'recurring': {'interval': 'month'}}}],
    payment_behavior='default_incomplete',
    payment_settings={'save_default_payment_method': 'on_subscription'},
)
print([k for k in sub.keys()])
if hasattr(sub, 'pending_setup_intent'):
    print("Has pending_setup_intent")
