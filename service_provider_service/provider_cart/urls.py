from django.urls import path
from .views import get_my_cart, add_to_cart, remove_from_cart, checkout_cart, get_purchased_plans, get_active_subscription, purchase_plan_direct, stripe_webhook, verify_payment

urlpatterns = [
    path("", get_my_cart, name="get-my-cart"),
    path("add/", add_to_cart, name="add-to-cart"),
    path("remove/<uuid:item_id>/", remove_from_cart, name="remove-from-cart"),
    path("checkout/", checkout_cart, name="checkout-cart"),
    path("purchase/", purchase_plan_direct, name="purchase-plan-direct"),
    path("webhook/", stripe_webhook, name="stripe-webhook"),
    path("verify-payment/", verify_payment, name="verify-payment"),
    path("purchased/", get_purchased_plans, name="get-purchased-plans"),
    path("subscription/active/", get_active_subscription, name="get-active-subscription"),
]
