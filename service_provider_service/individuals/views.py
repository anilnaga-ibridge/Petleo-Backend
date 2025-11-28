from django.shortcuts import render

# Create your views here.
from rest_framework import generics, permissions
from .models import IndividualProfile
from .serializers import IndividualProfileSerializer
from django.shortcuts import get_object_or_404
from service_provider.models import VerifiedUser

class IndividualProfileCreateView(generics.CreateAPIView):
    serializer_class = IndividualProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

class IndividualProfileDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = IndividualProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        auth_user_id = self.request.parser_context.get("kwargs", {}).get("auth_user_id") or self.request.user.id
        # Prefer provided auth_user_id param; fallback to authenticated user's id
        return get_object_or_404(IndividualProfile, verified_user__auth_user_id=auth_user_id)
