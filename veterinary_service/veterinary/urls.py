
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClinicViewSet, PetOwnerViewSet, PetViewSet, VisitViewSet, 
    DynamicFieldDefinitionViewSet, DynamicEntityViewSet,
    FormDefinitionViewSet,
    LabViewSet, PharmacyViewSet, ReminderViewSet,
    VisitQueueViewSet, AnalyticsViewSet, PetOwnerClientViewSet,
    LabTestTemplateViewSet, LabOrderViewSet
)

router = DefaultRouter()
router.register(r'clinics', ClinicViewSet, basename='clinics')
router.register(r'owners', PetOwnerViewSet, basename='owners')
router.register(r'pets', PetViewSet, basename='pets')
router.register(r'visits', VisitViewSet, basename='visits')
router.register(r'visits/queues', VisitQueueViewSet, basename='visit-queues')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')
router.register(r'pet-owner', PetOwnerClientViewSet, basename='pet-owner-app')

router.register(r'field-definitions', DynamicFieldDefinitionViewSet, basename='field-definitions')
router.register(r'forms/definitions', FormDefinitionViewSet, basename='form-definitions')
router.register(r'lab', LabViewSet, basename='lab')
router.register(r'pharmacy', PharmacyViewSet, basename='pharmacy')
router.register(r'reminders', ReminderViewSet, basename='reminders')

# Professional Lab Routes
router.register(r'lab-templates', LabTestTemplateViewSet)
router.register(r'lab-orders', LabOrderViewSet)

# Custom route for generic dynamic entities
dynamic_entity_list = DynamicEntityViewSet.as_view({'post': 'create'})

# Staff Assignment Routes
from .views import StaffAssignmentViewSet
router.register(r'assignments', StaffAssignmentViewSet, basename='assignments')


urlpatterns = [
    path('', include(router.urls)),
    path('entities/', dynamic_entity_list, name='dynamic-entities'),
]
