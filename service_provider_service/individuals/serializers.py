from rest_framework import serializers
from .models import IndividualProfile

class IndividualProfileSerializer(serializers.ModelSerializer):
    auth_user_id = serializers.UUIDField(write_only=True, required=True)

    class Meta:
        model = IndividualProfile
        fields = [
            "id", "auth_user_id", "display_name", "bio",
            "skills", "experience_years", "profile_image",
            "is_completed", "created_at", "updated_at"
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def create(self, validated_data):
        auth_user_id = validated_data.pop("auth_user_id")
        # verified_user relation is stored using to_field auth_user_id
        validated_data["verified_user_id"] = auth_user_id
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Do not allow changing verified_user
        validated_data.pop("auth_user_id", None)
        return super().update(instance, validated_data)
