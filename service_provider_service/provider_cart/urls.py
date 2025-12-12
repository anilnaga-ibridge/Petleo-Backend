from django.urls import path
from .views import get_my_cart, add_to_cart, remove_from_cart, checkout_cart, get_purchased_plans

urlpatterns = [
    path("", get_my_cart, name="get-my-cart"),
    path("add/", add_to_cart, name="add-to-cart"),
    path("remove/<uuid:item_id>/", remove_from_cart, name="remove-from-cart"),
    path("checkout/", checkout_cart, name="checkout-cart"),
    path("purchased/", get_purchased_plans, name="get-purchased-plans"),
]
