from rest_framework import serializers
from .models import Booking, BookingItem, BookingStatusHistory, VisitGroup


class BookingStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingStatusHistory
        fields = ['id', 'previous_status', 'new_status', 'changed_by', 'changed_at']
        read_only_fields = fields


class BookingSerializer(serializers.ModelSerializer):
    status_history = BookingStatusHistorySerializer(many=True, read_only=True)
    pet_details = serializers.SerializerMethodField()
    owner_details = serializers.SerializerMethodField()
    pet_name = serializers.SerializerMethodField()
    service_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    facility_name = serializers.SerializerMethodField()
    provider_name = serializers.SerializerMethodField()

    # Proxy fields from first BookingItem for frontend support
    provider_id = serializers.SerializerMethodField()
    service_id = serializers.SerializerMethodField()
    facility_id = serializers.SerializerMethodField()
    pet = serializers.SerializerMethodField()
    selected_time = serializers.SerializerMethodField()
    assigned_employee_id = serializers.SerializerMethodField()
    service_snapshot = serializers.SerializerMethodField()
    item_id = serializers.SerializerMethodField()
    completion_otp = serializers.SerializerMethodField()
    rejection_reason = serializers.SerializerMethodField()
    completed_at = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'owner_id', 'owner_details', 'provider_id', 'assigned_employee_id',
            'pet', 'pet_details', 'pet_name',
            'provider_name', 'service_name', 'category_name', 'facility_name',
            'service_id', 'facility_id', 'selected_time', 'address_snapshot', 'service_snapshot',
            'notes', 'status', 'rejection_reason', 'completed_at', 'created_at',
            'updated_at', 'status_history', 'item_id', 'completion_otp', 'total_price',
            'payment_status', 'payment_gateway', 'transaction_id', 'checkout_session_url'
        ]
        read_only_fields = [
            'id', 'owner_id', 'status', 'rejection_reason', 'created_at', 'updated_at',
            'status_history', 'pet_details', 'owner_details', 'pet_name', 'item_id', 'completion_otp',
            'payment_status', 'payment_gateway', 'transaction_id', 'checkout_session_url'
        ]

    def _get_first_item(self, obj):
        try:
            items = list(obj.items.all())
            return items[0] if items else None
        except Exception:
            return None

    def _snapshot(self, obj, snap_key='service_snapshot'):
        """Return a snapshot dict for the first item, or {}."""
        item = self._get_first_item(obj)
        snap = getattr(item, snap_key, None)
        return snap if isinstance(snap, dict) else {}

    # ── Per-booking item proxy fields ──────────────────────────────────────────

    def get_pet_details(self, obj):
        item = self._get_first_item(obj)
        return item.pet_snapshot if item else None

    def get_owner_details(self, obj):
        # Prefer item level snapshot or header level
        item = self._get_first_item(obj)
        return (item.owner_snapshot if item else None) or obj.owner_snapshot

    def get_pet_name(self, obj):
        snap = self._snapshot(obj, 'pet_snapshot')
        return snap.get('name') or 'Pet'

    def get_provider_id(self, obj):
        item = self._get_first_item(obj)
        return str(item.provider_id) if item else None

    def get_service_id(self, obj):
        item = self._get_first_item(obj)
        return str(item.service_id) if (item and item.service_id) else None

    def get_facility_id(self, obj):
        item = self._get_first_item(obj)
        return str(item.facility_id) if (item and item.facility_id) else None

    def get_pet(self, obj):
        item = self._get_first_item(obj)
        return str(item.pet_id) if (item and item.pet_id) else None

    def get_selected_time(self, obj):
        item = self._get_first_item(obj)
        return item.selected_time if item else None

    def get_assigned_employee_id(self, obj):
        item = self._get_first_item(obj)
        return str(item.assigned_employee_id) if (item and item.assigned_employee_id) else None

    def get_service_snapshot(self, obj):
        return self._snapshot(obj)

    def get_item_id(self, obj):
        item = self._get_first_item(obj)
        return str(item.id) if item else None

    def get_completion_otp(self, obj):
        item = self._get_first_item(obj)
        return item.completion_otp if item else None

    def get_rejection_reason(self, obj):
        item = self._get_first_item(obj)
        return item.rejection_reason if item else None

    def get_completed_at(self, obj):
        item = self._get_first_item(obj)
        return item.completed_at if item else None

    # ── Snapshot-derived display fields ────────────────────────────────────────

    def get_provider_name(self, obj):
        return self._snapshot(obj).get('provider_name') or 'Service Provider'

    def get_service_name(self, obj):
        return self._snapshot(obj).get('service_name') or 'General Service'

    def get_category_name(self, obj):
        snap = self._snapshot(obj)
        return snap.get('category_name') or snap.get('service_name') or ''

    def get_facility_name(self, obj):
        return self._snapshot(obj).get('facility_name') or ''


class BookingItemSerializer(serializers.ModelSerializer):
    """
    Serializer for a single BookingItem.
    """
    service_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    facility_name = serializers.SerializerMethodField()
    provider_name = serializers.SerializerMethodField()
    pet_name = serializers.SerializerMethodField()

    class Meta:
        model = BookingItem
        fields = [
            'id', 'booking', 'provider_id', 'assigned_employee_id', 'resource_id',
            'pet_id', 'owner_id', 'pet_snapshot', 'owner_snapshot', 'employee_snapshot',
            'service_id', 'facility_id', 'selected_time', 'end_time',
            'service_snapshot', 'price_snapshot', 'addons_snapshot',
            'notes', 'status', 'rejection_reason',
            'completion_otp', 'otp_expires_at', 'completed_at',
            'created_at', 'updated_at',
            'service_name', 'category_name', 'facility_name', 'provider_name', 'pet_name'
        ]
        read_only_fields = [
            'id', 'booking', 'status', 'rejection_reason',
            'completion_otp', 'otp_expires_at', 'completed_at',
            'created_at', 'updated_at',
            'service_name', 'category_name', 'facility_name', 'provider_name', 'pet_name'
        ]

    def _snap(self, obj, snap_key='service_snapshot'):
        snap = getattr(obj, snap_key, None)
        return snap if isinstance(snap, dict) else {}

    def get_provider_name(self, obj):
        return self._snap(obj).get('provider_name') or 'Service Provider'

    def get_service_name(self, obj):
        return self._snap(obj).get('service_name') or 'General Service'

    def get_category_name(self, obj):
        snap = self._snap(obj)
        return snap.get('category_name') or snap.get('service_name') or ''

    def get_facility_name(self, obj):
        return self._snap(obj).get('facility_name') or ''

    def get_pet_name(self, obj):
        return self._snap(obj, 'pet_snapshot').get('name') or 'Pet'


class VisitGroupSerializer(serializers.ModelSerializer):
    items = BookingItemSerializer(many=True, read_only=True)

    class Meta:
        model = VisitGroup
        fields = [
            'id', 'organization_id', 'pet_id', 'owner_id', 
            'idempotency_key', 'status', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']


from .models import SubscriptionPlan, ProviderSubscription, SubscriptionPayment

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'description', 'price', 'currency',
            'billing_cycle', 'trial_days', 'is_active', 'features', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SubscriptionPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPayment
        fields = [
            'id', 'subscription', 'amount', 'currency', 'status',
            'payment_gateway', 'transaction_id', 'checkout_session_url', 'error_message', 'created_at'
        ]
        read_only_fields = ['id', 'subscription', 'created_at']


class ProviderSubscriptionSerializer(serializers.ModelSerializer):
    plan_details = SubscriptionPlanSerializer(source='plan', read_only=True)
    payments = SubscriptionPaymentSerializer(many=True, read_only=True)

    class Meta:
        model = ProviderSubscription
        fields = [
            'id', 'provider_id', 'plan', 'plan_details', 'status',
            'start_date', 'end_date', 'trial_end_date', 'auto_renew', 'external_subscription_id', 'payments',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'start_date', 'end_date', 'trial_end_date', 'payments',
            'created_at', 'updated_at'
        ]
