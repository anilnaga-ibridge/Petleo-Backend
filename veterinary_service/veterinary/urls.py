
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClinicViewSet, PetOwnerViewSet, PetViewSet, VisitViewSet, 
    DynamicFieldDefinitionViewSet, DynamicEntityViewSet,
    FormDefinitionViewSet,
    LabViewSet, PharmacyViewSet, ReminderViewSet,
    VisitQueueViewSet, AnalyticsViewSet, PetOwnerClientViewSet
)

router = DefaultRouter()
router.register(r'clinics', ClinicViewSet)
router.register(r'owners', PetOwnerViewSet)
router.register(r'pets', PetViewSet)
router.register(r'visits', VisitViewSet)
router.register(r'visits/queues', VisitQueueViewSet, basename='visit-queues')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')
router.register(r'pet-owner', PetOwnerClientViewSet, basename='pet-owner-app')

router.register(r'field-definitions', DynamicFieldDefinitionViewSet)
router.register(r'forms/definitions', FormDefinitionViewSet)
router.register(r'lab', LabViewSet, basename='lab')
router.register(r'pharmacy', PharmacyViewSet, basename='pharmacy')
router.register(r'reminders', ReminderViewSet, basename='reminders')

# Custom route for generic dynamic entities
dynamic_entity_list = DynamicEntityViewSet.as_view({'post': 'create'})

urlpatterns = [
    path('', include(router.urls)),
    path('entities/', dynamic_entity_list, name='dynamic-entities'),
]
