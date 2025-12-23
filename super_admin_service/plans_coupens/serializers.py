
from rest_framework import serializers
from .models import BillingCycle, Plan, PlanPrice, PlanCapability, Coupon,PurchasedPlan,ProviderPlanCapability
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


class PlanCapabilitySerializer(serializers.ModelSerializer):
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
    facility_id = serializers.PrimaryKeyRelatedField(
        queryset=Facility.objects.all(),
        source="facility",
        write_only=True,
        allow_null=True,
        required=False
    )

    # READ FIELDS
    plan = SimplePlanSerializer(read_only=True)
    service = SimpleServiceSerializer(read_only=True)
    category = SimpleCategorySerializer(read_only=True)
    facility = SimpleFacilitySerializer(read_only=True)

    class Meta:
        model = PlanCapability
        fields = [
            "id",
            "plan", "plan_id",
            "service", "service_id",
            "category", "category_id",
            "facility", "facility_id",
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

        # Prevent duplicate combinations
        plan = data.get("plan") or (self.instance.plan if self.instance else None)
        service = data.get("service") or (self.instance.service if self.instance else None)
        category = data.get("category") or (self.instance.category if self.instance else None)
        facility = data.get("facility") or (self.instance.facility if self.instance else None)

        qs = PlanCapability.objects.filter(plan=plan, service=service, category=category, facility=facility)

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                "This combination of plan, service, category, and facility already exists."
            )

        return data


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
    capabilities = PlanCapabilitySerializer(many=True, required=False)
    features = serializers.ListField(child=serializers.CharField(), required=False)

    class Meta:
        model = Plan
        fields = [
            "id", "title", "slug", "role", "subtitle", "description",
            "features", "default_billing_cycle", "default_billing_cycle_id",
            "is_active", "created_at", "updated_at",
            "prices", "capabilities",
        ]
        read_only_fields = ("slug", "created_at", "updated_at")

    def create(self, validated_data):
        prices = validated_data.pop("prices", [])
        capabilities = validated_data.pop("capabilities", [])

        if "features" not in validated_data:
            validated_data["features"] = []

        plan = Plan.objects.create(**validated_data)

        # create nested prices
        for p in prices:
            PlanPrice.objects.create(plan=plan, **p)

        # create nested capabilities
        for cap in capabilities:
            PlanCapability.objects.create(plan=plan, **cap)

        return plan

    def update(self, instance, validated_data):
        prices = validated_data.pop("prices", None)
        capabilities = validated_data.pop("capabilities", None)

        # simple field update
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()

        # replace prices on update
        if prices is not None:
            instance.prices.all().delete()
            for p in prices:
                PlanPrice.objects.create(plan=instance, **p)

        # replace capabilities on update
        if capabilities is not None:
            instance.capabilities.all().delete()
            for cap in capabilities:
                PlanCapability.objects.create(plan=instance, **cap)

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


class ProviderPlanCapabilitySerializer(serializers.ModelSerializer):
    facility = FacilitySerializer(read_only=True)

    class Meta:
        model = ProviderPlanCapability
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
        """
        Groups flat PlanCapability rows into a hierarchical structure:
        Service -> Category -> Facilities
        """
        capabilities = obj.capabilities.select_related(
            "service", "category", "facility"
        ).order_by("service__display_name", "category__name")

        # Structure:
        # {
        #   service_id: {
        #       service_info: {...},
        #       categories: {
        #           category_id: {
        #               category_info: {...},
        #               permissions: {...},
        #               facilities: [...]
        #           }
        #       }
        #   }
        # }
        
        grouped = {}

        for cap in capabilities:
            if not cap.service:
                continue
            
            s_id = str(cap.service.id)
            if s_id not in grouped:
                grouped[s_id] = {
                    "service": {
                        "id": s_id,
                        "name": cap.service.display_name,
                    },
                    "categories": {}
                }
            
            if cap.category:
                c_id = str(cap.category.id)
                if c_id not in grouped[s_id]["categories"]:
                    grouped[s_id]["categories"][c_id] = {
                        "id": c_id,
                        "name": cap.category.name,
                        "permissions": {
                            "can_view": False,
                            "can_create": False,
                            "can_edit": False,
                            "can_delete": False,
                        },
                        "facilities": []
                    }
                
                # If this capability is for the category itself (no facility), set permissions
                if not cap.facility:
                    grouped[s_id]["categories"][c_id]["permissions"] = {
                        "can_view": cap.can_view,
                        "can_create": cap.can_create,
                        "can_edit": cap.can_edit,
                        "can_delete": cap.can_delete,
                    }
                else:
                    # It's a facility capability
                    grouped[s_id]["categories"][c_id]["facilities"].append({
                        "id": str(cap.facility.id),
                        "name": cap.facility.name,
                        "permissions": {
                            "can_view": cap.can_view,
                            "can_create": cap.can_create,
                            "can_edit": cap.can_edit,
                            "can_delete": cap.can_delete,
                        }
                    })

        # Convert to list format
        result = []
        for s_key, s_val in grouped.items():
            cats_list = []
            for c_key, c_val in s_val["categories"].items():
                cats_list.append(c_val)
            
            result.append({
                "service": s_val["service"],
                "categories": cats_list
            })
            
        return result
