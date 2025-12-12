





from rest_framework import serializers
from .models import BillingCycle, Plan, PlanPrice, PlanItem, Coupon,PurchasedPlan,ProviderPlanPermission
from dynamic_services.models import Service
from dynamic_categories.models import Category
from dynamic_facilities.serializers import FacilitySerializer
from dynamic_facilities.models import Facility


class BillingCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingCycle
        fields = "__all__"


class PlanPriceSerializer(serializers.ModelSerializer):

    plan = serializers.SerializerMethodField()
    billing_cycle = BillingCycleSerializer(read_only=True)

    billing_cycle_id = serializers.PrimaryKeyRelatedField(
        queryset=BillingCycle.objects.all(),
        source="billing_cycle",
        write_only=True
    )

    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.all(),
        source="plan",
        write_only=True
    )

    class Meta:
        model = PlanPrice
        fields = [
            "id",
            "plan",          # nested
            "plan_id",       # write-only
            "billing_cycle",
            "billing_cycle_id",
            "amount",
            "currency",
            "is_active",
        ]

    def get_plan(self, obj):
        return {
            "id": obj.plan.id,
            "title": obj.plan.title,
            "slug": obj.plan.slug,
            "role": obj.plan.role,
        }






class SimplePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ["id", "title"]


class SimpleServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "display_name"]


class SimpleCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class SimpleFacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = ["id", "name"]


class PlanItemSerializer(serializers.ModelSerializer):
    # WRITE FIELDS
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.all(),
        source="plan",
        write_only=True
    )
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(),
        source="service",
        write_only=True,
        allow_null=True,
        required=False
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        allow_null=True,
        required=False
    )

    facilities = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Facility.objects.all(),
        write_only=True
    )

    # READ FIELDS
    plan = SimplePlanSerializer(read_only=True)
    service = SimpleServiceSerializer(read_only=True)
    category = SimpleCategorySerializer(read_only=True)
    facilities_detail = SimpleFacilitySerializer(
        many=True,
        read_only=True,
        source="facilities"
    )

    class Meta:
        model = PlanItem
        fields = [
            "id",

            "plan", "plan_id",
            "service", "service_id",
            "category", "category_id",

            "facilities",
            "facilities_detail",

            "can_view",
            "can_create",
            "can_edit",
            "can_delete",
        ]

    def validate(self, data):
        # Must have service OR category
        if not data.get("service") and not data.get("category"):
            raise serializers.ValidationError(
                "Either service_id or category_id is required."
            )

        # Extra safety: if both provided, OK (some systems use both)
        plan = data.get("plan") or (self.instance.plan if self.instance else None)
        service = data.get("service") or (self.instance.service if self.instance else None)
        category = data.get("category") or (self.instance.category if self.instance else None)

        # Prevent duplicate combinations
        qs = PlanItem.objects.filter(plan=plan, service=service, category=category)

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                "This combination of plan, service, and category already exists."
            )

        return data

    def create(self, validated_data):
        facilities = validated_data.pop("facilities", [])
        item = PlanItem.objects.create(**validated_data)
        item.facilities.set(facilities)
        return item

    def update(self, instance, validated_data):
        facilities = validated_data.pop("facilities", None)

        for attr, val in validated_data.items():
            setattr(instance, attr, val)

        instance.save()

        if facilities is not None:
            instance.facilities.set(facilities)

        return instance




class PlanSerializer(serializers.ModelSerializer):
    default_billing_cycle = BillingCycleSerializer(read_only=True)
    default_billing_cycle_id = serializers.PrimaryKeyRelatedField(
        queryset=BillingCycle.objects.all(),
        source="default_billing_cycle",
        write_only=True,
        required=False,
        allow_null=True
    )

    prices = PlanPriceSerializer(many=True, required=False)
    items = PlanItemSerializer(many=True, required=False)
    features = serializers.ListField(child=serializers.CharField(), required=False)

    class Meta:
        model = Plan
        fields = [
            "id", "title", "slug", "role", "subtitle", "description",
            "features", "default_billing_cycle", "default_billing_cycle_id",
            "is_active", "created_at", "updated_at",
            "prices", "items",
        ]
        read_only_fields = ("slug", "created_at", "updated_at")

    def create(self, validated_data):
        prices = validated_data.pop("prices", [])
        items = validated_data.pop("items", [])

        if "features" not in validated_data:
            validated_data["features"] = []

        plan = Plan.objects.create(**validated_data)

        # create nested prices
        for p in prices:
            PlanPrice.objects.create(plan=plan, **p)

        # create nested items
        for it in items:
            facilities = it.pop("facilities", [])
            item = PlanItem.objects.create(plan=plan, **it)
            if facilities:
                item.facilities.set(facilities)

        return plan

    def update(self, instance, validated_data):
        prices = validated_data.pop("prices", None)
        items = validated_data.pop("items", None)

        # simple field update
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()

        # replace prices on update
        if prices is not None:
            instance.prices.all().delete()
            for p in prices:
                PlanPrice.objects.create(plan=instance, **p)

        # replace items on update
        if items is not None:
            instance.items.all().delete()
            for it in items:
                facilities = it.pop("facilities", [])
                item = PlanItem.objects.create(plan=instance, **it)
                if facilities:
                    item.facilities.set(facilities)

        return instance

class CouponSerializer(serializers.ModelSerializer):
    applies_to_plans = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.all(), many=True, required=False
    )

    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "discount_type",
            "discount_value",
            "max_uses",
            "used_count",
            "start_date",
            "end_date",
            "applicable_roles",
            "applies_to_plans",
            "min_amount",
            "max_amount",
            "is_active",
            "created_at",
        ]

    def validate(self, data):
        # Percentage cannot exceed 100
        if data.get("discount_type") == "percent" and data.get("discount_value") > 100:
            raise serializers.ValidationError("Percent discount cannot exceed 100.")
        return data



class PurchasedPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchasedPlan
        fields = "__all__"


class ProviderPlanPermissionSerializer(serializers.ModelSerializer):
    facilities = FacilitySerializer(many=True, read_only=True)

    class Meta:
        model = ProviderPlanPermission
        fields = "__all__"



class ProviderPlanViewSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    billing_cycle = BillingCycleSerializer(
        read_only=True, source="default_billing_cycle"
    )
    access = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            "id",
            "title",
            "subtitle",
            "description",
            "features",
            "price",
            "billing_cycle",
            "access",
            "is_active",
        ]

    def get_price(self, obj):
        price = obj.prices.filter(is_active=True).first()
        if not price:
            return None
        return {
            "amount": str(price.amount),
            "currency": price.currency
        }

    def get_access(self, obj):
        items = obj.items.select_related(
            "service"
        ).prefetch_related("facilities")

        data = []
        for item in items:
            if not item.service:
                continue

            # Fetch all categories belonging to this service
            service_categories = item.service.categories.all()

            cats_data = []
            for cat in service_categories:
                cats_data.append({
                    "id": str(cat.id),
                    "name": cat.name,
                    "permissions": {
                        "can_view": item.can_view,
                        "can_create": item.can_create,
                        "can_edit": item.can_edit,
                        "can_delete": item.can_delete,
                    },
                    "facilities": [
                        {
                            "id": str(f.id),
                            "name": f.name
                        }
                        for f in item.facilities.all()
                    ]
                })

            data.append({
                "service": {
                    "id": str(item.service.id),
                    "name": item.service.display_name,
                },
                "categories": cats_data
            })
        return data
