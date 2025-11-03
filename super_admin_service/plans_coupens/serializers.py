# from rest_framework import serializers
# from .models import BillingCycle, Plan, PlanPrice, PlanItem, Coupon


# class BillingCycleSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = BillingCycle
#         fields = "__all__"
#         ordering = ["duration_value"]


# class PlanItemSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PlanItem
#         exclude = ["plan"]


# class PlanPriceSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PlanPrice
#         exclude = ["plan"]


# class PlanSerializer(serializers.ModelSerializer):
#     prices = PlanPriceSerializer(many=True)
#     items = PlanItemSerializer(many=True)

#     class Meta:
#         model = Plan
#         fields = "__all__"

#     def create(self, validated_data):
#         prices_data = validated_data.pop("prices", [])
#         items_data = validated_data.pop("items", [])
#         plan = Plan.objects.create(**validated_data)

#         for price in prices_data:
#             PlanPrice.objects.create(plan=plan, **price)
#         for item in items_data:
#             PlanItem.objects.create(plan=plan, **item)
#         return plan

#     def update(self, instance, validated_data):
#         prices_data = validated_data.pop("prices", [])
#         items_data = validated_data.pop("items", [])
#         for attr, value in validated_data.items():
#             setattr(instance, attr, value)
#         instance.save()

#         instance.prices.all().delete()
#         instance.items.all().delete()

#         for price in prices_data:
#             PlanPrice.objects.create(plan=instance, **price)
#         for item in items_data:
#             PlanItem.objects.create(plan=instance, **item)

#         return instance


# class CouponSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Coupon
#         fields = "__all__"
from rest_framework import serializers
from .models import BillingCycle, Plan, PlanPrice, PlanItem, Coupon
from dynamic_services.models import Service
from dynamic_categories.models import Category


class BillingCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingCycle
        fields = "__all__"


class PlanPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanPrice
        exclude = ("plan",)


class PlanItemSerializer(serializers.ModelSerializer):
    """
    Serializer for individual PlanItem (matches the actual model)
    """
    class Meta:
        model = PlanItem
        exclude = ("plan",)


class PlanItemGroupSerializer(serializers.Serializer):
    """
    Input format: One service → multiple categories
    Example:
    {
        "service": "uuid-of-grooming-service",
        "categories": ["uuid-of-bathing-category", "uuid-of-nail-cutting-category"],
        "can_view": true,
        "can_create": true
    }
    """
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all())
    categories = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), many=True)
    can_view = serializers.BooleanField(default=False)
    can_create = serializers.BooleanField(default=False)
    can_edit = serializers.BooleanField(default=False)
    can_delete = serializers.BooleanField(default=False)

    def validate(self, data):
        service = data["service"]
        for category in data["categories"]:
            if category.service_id != service.id:
                raise serializers.ValidationError(
                    f"Category '{category.name}' does not belong to Service '{service.display_name}'."
                )
        return data


# class PlanSerializer(serializers.ModelSerializer):
#     prices = PlanPriceSerializer(many=True, required=False)
#     items = PlanItemSerializer(many=True, required=False, read_only=True)
#     item_groups = PlanItemGroupSerializer(many=True, required=False, write_only=True)

#     class Meta:
#         model = Plan
#         fields = [
#             "id", "title", "slug", "role_name", "role",
#             "subtitle", "description", "features", "is_active",
#             "default_billing_cycle", "prices", "items", "item_groups"
#         ]

#     def create(self, validated_data):
#         prices_data = validated_data.pop("prices", [])
#         items_grouped_data = validated_data.pop("item_groups", [])
#         plan = Plan.objects.create(**validated_data)

#         # Create related PlanPrice objects
#         for price_data in prices_data:
#             PlanPrice.objects.create(plan=plan, **price_data)

#         # Create related PlanItem objects
#         for group in items_grouped_data:
#             service = group["service"]
#             categories = group["categories"]
#             permissions = {
#                 "can_view": group.get("can_view", False),
#                 "can_create": group.get("can_create", False),
#                 "can_edit": group.get("can_edit", False),
#                 "can_delete": group.get("can_delete", False),
#             }
#             for category in categories:
#                 PlanItem.objects.create(
#                     plan=plan,
#                     service=service,
#                     category=category,
#                     **permissions
#                 )

#         return plan
class PlanSerializer(serializers.ModelSerializer):
    prices = PlanPriceSerializer(many=True, required=False)
    items = PlanItemSerializer(many=True, required=False)

    class Meta:
        model = Plan
        fields = "__all__"

    def update(self, instance, validated_data):
        # Extract nested data
        prices_data = validated_data.pop('prices', None)
        items_data = validated_data.pop('items', None)

        # --- Update the Plan fields ---
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # --- Update PlanPrice ---
        if prices_data is not None:
            instance.prices.all().delete()
            for price_data in prices_data:
                PlanPrice.objects.create(plan=instance, **price_data)

        # --- Update PlanItem ---
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                PlanItem.objects.create(plan=instance, **item_data)

        return instance


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = "__all__"
