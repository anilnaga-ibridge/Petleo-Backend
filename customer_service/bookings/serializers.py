from rest_framework import serializers
from .models import Booking, BookingItem, BookingStatusHistory
from pets.serializers import PetListSerializer
from customers.serializers import PetOwnerProfileSerializer


class BookingStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingStatusHistory
        fields = ['id', 'previous_status', 'new_status', 'changed_by', 'changed_at']
        read_only_fields = fields


class BookingSerializer(serializers.ModelSerializer):
    status_history = BookingStatusHistorySerializer(many=True, read_only=True)
    pet_details = serializers.SerializerMethodField()
    owner_details = PetOwnerProfileSerializer(source='owner', read_only=True)
    pet_name = serializers.CharField(source='pet.name', read_only=True)
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
            'id', 'owner', 'owner_details', 'provider_id', 'assigned_employee_id',
            'pet', 'pet_details', 'pet_name',
            'provider_name', 'service_name', 'category_name', 'facility_name',
            'service_id', 'facility_id', 'selected_time', 'address_snapshot', 'service_snapshot',
            'notes', 'status', 'rejection_reason', 'completed_at', 'created_at',
            'updated_at', 'status_history', 'item_id', 'completion_otp', 'total_price'
        ]
        read_only_fields = [
            'id', 'owner', 'status', 'rejection_reason', 'created_at', 'updated_at',
            'status_history', 'pet_details', 'owner_details', 'pet_name', 'item_id', 'completion_otp'
        ]

    def _get_first_item(self, obj):
        """
        Return the first BookingItem for this booking.

        IMPORTANT: This method intentionally uses obj.items.all() rather than
        obj.items.first() so that it benefits from Django's prefetch_related cache.

        When the ViewSet calls:
            queryset.prefetch_related('items')

        Django pre-loads ALL items into obj._prefetched_objects_cache['items'].
        Calling obj.items.all() returns the cached list (zero DB queries).
        Calling obj.items.first() bypasses the cache and hits the DB every time.

        This design guarantees:
        1. No N+1 database queries when listing many bookings.
        2. Each booking always gets ITS OWN item — no cross-booking bleeding.
        3. Works correctly even without prefetch (falls back gracefully to a DB call).
        """
        try:
            items = list(obj.items.all())
            return items[0] if items else None
        except Exception:
            return None

    def _snapshot(self, obj):
        """Return the service_snapshot dict for the first item, or {}."""
        item = self._get_first_item(obj)
        snap = getattr(item, 'service_snapshot', None)
        return snap if isinstance(snap, dict) else {}

    # ── Per-booking item proxy fields ──────────────────────────────────────────

    def get_pet_details(self, obj):
        item = self._get_first_item(obj)
        return PetListSerializer(item.pet).data if (item and item.pet) else None

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

    def validate_pet(self, value):
        return value


class BookingItemSerializer(serializers.ModelSerializer):
    """
    Serializer for a single BookingItem.
    Snapshot fields are read straight from the item's own service_snapshot dict.
    """
    pet_details = PetListSerializer(source='pet', read_only=True)
    service_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    facility_name = serializers.SerializerMethodField()
    provider_name = serializers.SerializerMethodField()

    class Meta:
        model = BookingItem
        fields = [
            'id', 'booking', 'provider_id', 'assigned_employee_id', 'pet', 'pet_details',
            'service_id', 'facility_id', 'selected_time', 'end_time',
            'service_snapshot', 'price_snapshot', 'addons_snapshot',
            'notes', 'status', 'rejection_reason',
            'completion_otp', 'otp_expires_at', 'completed_at',
            'created_at', 'updated_at',
            'service_name', 'category_name', 'facility_name', 'provider_name',
        ]
        read_only_fields = [
            'id', 'booking', 'status', 'rejection_reason',
            'completion_otp', 'otp_expires_at', 'completed_at',
            'created_at', 'updated_at', 'pet_details',
            'service_name', 'category_name', 'facility_name', 'provider_name',
        ]

    def _snap(self, obj):
        snap = getattr(obj, 'service_snapshot', None)
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
