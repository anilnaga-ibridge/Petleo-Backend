from django.test import TestCase
from django.utils import timezone
from django.core.management import call_command
from django.contrib.auth import get_user_model
from .models import Plan, BillingCycle, PurchasedPlan, ProviderPlanPermission
from .services import calculate_end_date
from datetime import timedelta

User = get_user_model()

class PlanExpiryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="test@example.com", password="password")
        self.plan = Plan.objects.create(title="Test Plan", role="individual")
        self.billing_cycle = BillingCycle.objects.create(
            name="Monthly", duration_value=1, duration_type="months"
        )

    def test_calculate_end_date(self):
        start = timezone.now()
        
        # Test 1 Month
        end = calculate_end_date(start, 1, "months")
        # Approximate check (since days in month vary)
        self.assertTrue(28 <= (end - start).days <= 31)

        # Test 1 Week
        end = calculate_end_date(start, 1, "weeks")
        self.assertEqual((end - start).days, 7)

    def test_expiry_endpoint(self):
        # Create an expired plan
        start_date = timezone.now() - timedelta(days=40)
        end_date = timezone.now() - timedelta(days=10)
        
        purchased = PurchasedPlan.objects.create(
            user=self.user,
            plan=self.plan,
            billing_cycle=self.billing_cycle,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )

        # Create permissions
        ProviderPlanPermission.objects.create(
            user=self.user, plan=self.plan, can_view=True
        )

        # Use APIClient for proper DRF testing
        from rest_framework.test import APIClient
        client = APIClient()
        
        self.user.is_superuser = True
        self.user.save()
        
        # Force authentication
        client.force_authenticate(user=self.user)
        
        # Mock Kafka producer to avoid NoBrokersAvailable error
        from unittest.mock import patch
        
        url = '/api/superadmin/purchased-plans/check-expiry/'
        with patch('plans_coupens.kafka_producer.publish_permissions_revoked') as mock_publish:
            response = client.post(url)
        
        self.assertEqual(response.status_code, 200)

        # Verify
        purchased.refresh_from_db()
        self.assertFalse(purchased.is_active)
        self.assertFalse(ProviderPlanPermission.objects.filter(user=self.user).exists())
