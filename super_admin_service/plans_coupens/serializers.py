from rest_framework import serializers
from .models import Plan, PlanCapability, Coupon, PurchasedPlan, ProviderPlanCapability, BillingCycleConfig
from dynamic_services.models import Service
from dynamic_categories.models import Category
from dynamic_facilities.serializers import FacilitySerializer
from dynamic_facilities.models import Facility

class BillingCycleConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingCycleConfig
        fields = "__all__"

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
            "limits",
            "permissions",
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
    capabilities = PlanCapabilitySerializer(many=True, required=False)
    features = serializers.ListField(child=serializers.CharField(), required=False)

    class Meta:
        model = Plan
        fields = [
            "id", "title", "slug", "target_type", "subtitle", "description",
            "features", "billing_cycle", "price", "currency",
            "is_active", "created_at", "updated_at",
            "capabilities",
        ]
        read_only_fields = ("slug", "created_at", "updated_at")

    def validate_billing_cycle(self, value):
        if not BillingCycleConfig.objects.filter(code=value, is_active=True).exists():
            raise serializers.ValidationError(f"Invalid billing cycle code: {value}")
        return value

    def create(self, validated_data):
        capabilities = validated_data.pop("capabilities", [])

        if "features" not in validated_data:
            validated_data["features"] = []

        plan = Plan.objects.create(**validated_data)

        # create nested capabilities
        for cap in capabilities:
            PlanCapability.objects.create(plan=plan, **cap)

        return plan

    def update(self, instance, validated_data):
        capabilities = validated_data.pop("capabilities", None)

        # simple field update
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()

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
            "currency",
            "billing_cycle",
            "access",
            "is_active",
        ]

    def get_access(self, obj):
        """
        Groups flat PlanCapability rows into a hierarchical structure:
        Service -> Category -> Facilities
        """
        capabilities = obj.capabilities.select_related(
            "service", "category", "facility"
        ).order_by("service__display_name", "category__name")

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
                        "permissions": cap.permissions,
                        "limits": cap.limits,
                        "facilities": []
                    }
                
                # If this capability is for the category itself (no facility), set permissions
                if not cap.facility:
                    grouped[s_id]["categories"][c_id]["permissions"] = cap.permissions
                    grouped[s_id]["categories"][c_id]["limits"] = cap.limits
                else:
                    # It's a facility capability
                    grouped[s_id]["categories"][c_id]["facilities"].append({
                        "id": str(cap.facility.id),
                        "name": cap.facility.name,
                        "permissions": cap.permissions,
                        "limits": cap.limits
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
