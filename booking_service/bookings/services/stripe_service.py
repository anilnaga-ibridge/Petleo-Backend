import stripe
from django.conf import settings
from rest_framework.exceptions import ValidationError

stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    @staticmethod
    def create_subscription_checkout_session(plan, success_url, cancel_url):
        """
        Create a checkout session for a provider subscription.
        Uses `mode="subscription"`.
        """
        try:
            # For subscriptions, price_data needs a recurring interval
            interval = 'month' if plan.billing_cycle == 'MONTHLY' else 'year'
            
            # Note: In production, you would typically use Stripe Product/Price IDs
            # But we can also use price_data for dynamic pricing
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': plan.currency.lower(),
                        'product_data': {
                            'name': plan.name,
                            'description': plan.description or 'Provider Subscription',
                        },
                        'unit_amount': int(plan.price * 100), # amount in cents/lowest denom
                        'recurring': {
                            'interval': interval,
                        },
                    },
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
            )
            return session
        except Exception as e:
            raise ValidationError(f"Error creating Stripe Session: {str(e)}")

    @staticmethod
    def create_booking_checkout_session(booking, service_name, total_price, success_url, cancel_url):
        """
        Create a checkout session for a pet owner booking.
        Uses `mode="payment"`.
        """
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': booking.currency.lower(),
                        'product_data': {
                            'name': service_name,
                        },
                        'unit_amount': int(total_price * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
            )
            return session
        except Exception as e:
            raise ValidationError(f"Error creating Stripe Session: {str(e)}")

    @staticmethod
    def verify_webhook_signature(payload, sig_header):
        """
        Verifies the Stripe webhook signature and returns the event object.
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            return event
        except ValueError as e:
            # Invalid payload
            raise ValidationError("Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            raise ValidationError("Invalid signature")
