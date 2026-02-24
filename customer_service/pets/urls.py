from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PetViewSet, PetMedicalProfileViewSet, PetDocumentViewSet,
    PetMedicationViewSet, PetVaccinationViewSet
)

router = DefaultRouter()
router.register(r'pets', PetViewSet, basename='pet')
router.register(r'medical-profiles', PetMedicalProfileViewSet, basename='medical-profile')
router.register(r'documents', PetDocumentViewSet, basename='pet-document')
router.register(r'medications', PetMedicationViewSet, basename='pet-medication')
router.register(r'vaccinations', PetVaccinationViewSet, basename='pet-vaccination')

urlpatterns = [
    path('', include(router.urls)),
]
