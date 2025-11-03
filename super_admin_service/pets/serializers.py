from rest_framework import serializers
from .models import PetType, PetBreed

class PetBreedSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetBreed
        fields = "__all__"


class PetTypeSerializer(serializers.ModelSerializer):
    breeds = PetBreedSerializer(many=True, read_only=True)

    class Meta:
        model = PetType
        fields = "__all__"
