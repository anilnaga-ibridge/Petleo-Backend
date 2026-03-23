from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClinicViewSet, PetOwnerViewSet, PetViewSet, VisitViewSet,
    DynamicFieldDefinitionViewSet, DynamicEntityViewSet,
    FormDefinitionViewSet,
    LabViewSet, PharmacyViewSet, ReminderViewSet,
    VisitQueueViewSet, AnalyticsViewSet, PetOwnerClientViewSet,
    LabTestTemplateViewSet, LabTestFieldViewSet, LabOrderViewSet,
    MedicalAppointmentViewSet, VeterinaryAvailabilityViewSet,
    CreateOnlineAppointmentView,
    LabTestViewSet, MedicineViewSet, PrescriptionViewSet,
    PharmacyTransactionViewSet, VisitInvoiceViewSet,
    StaffAssignmentViewSet,
    TreatmentEstimateViewSet, EstimateLineItemViewSet,
    MedicineReminderViewSet, MedicineReminderScheduleViewSet,
    PreVisitFormViewSet, DashboardViewSet,
    PharmacyOrderViewSet, MedicineViewSet, MedicineBatchViewSet,
)

router = DefaultRouter()
router.register(r'clinics', ClinicViewSet, basename='clinics')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'pre-visit', PreVisitFormViewSet, basename='pre-visit-forms')
router.register(r'owners', PetOwnerViewSet, basename='owners')
router.register(r'pets', PetViewSet, basename='pets')
router.register(r'visits', VisitViewSet, basename='visits')
router.register(r'visits/queues', VisitQueueViewSet, basename='visit-queues')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')
router.register(r'pet-owner', PetOwnerClientViewSet, basename='pet-owner-app')
router.register(r'appointments', MedicalAppointmentViewSet, basename='appointments')
router.register(r'availability', VeterinaryAvailabilityViewSet, basename='availability')

router.register(r'field-definitions', DynamicFieldDefinitionViewSet, basename='field-definitions')
router.register(r'forms/definitions', FormDefinitionViewSet, basename='form-definitions')
router.register(r'lab', LabViewSet, basename='lab')
router.register(r'pharmacy', PharmacyViewSet, basename='pharmacy')
router.register(r'reminders', MedicineReminderViewSet, basename='reminders')
router.register(r'medicine-reminders', MedicineReminderViewSet, basename='medicine-reminders')
router.register(r'medicine-schedules', MedicineReminderScheduleViewSet, basename='medicine-schedules')

# Professional Lab Routes
router.register(r'lab-templates', LabTestTemplateViewSet)
router.register(r'lab-template-fields', LabTestFieldViewSet, basename='lab-template-fields')
router.register(r'lab-orders', LabOrderViewSet)

# Next Gen Engine Routes
router.register(r'catalog/lab-tests', LabTestViewSet, basename='catalog-lab-tests')
router.register(r'catalog/medicines', MedicineViewSet, basename='catalog-medicines')
router.register(r'prescriptions', PrescriptionViewSet, basename='prescriptions')
router.register(r'pharmacy/transactions', PharmacyTransactionViewSet, basename='pharmacy-transactions')
router.register(r'billing/invoices', VisitInvoiceViewSet, basename='billing-invoices')
router.register(r'billing/estimates', TreatmentEstimateViewSet, basename='billing-estimates')
router.register(r'billing/estimates/items', EstimateLineItemViewSet, basename='billing-estimate-items')

# SaaS Pharmacy Fulfillment Route
router.register(r'pharmacy-orders', PharmacyOrderViewSet, basename='pharmacy-orders')
router.register(r'pharmacy/inventory', MedicineViewSet, basename='pharmacy-inventory')
router.register(r'pharmacy/batches', MedicineBatchViewSet, basename='pharmacy-batches')

# Custom route for generic dynamic entities
from .views import DynamicEntityViewSet
dynamic_entity_list = DynamicEntityViewSet.as_view({'post': 'create'})

router.register(r'assignments', StaffAssignmentViewSet, basename='assignments')

from .views import VaccineMasterViewSet, PetVaccinationRecordViewSet
router.register(r'vaccines', VaccineMasterViewSet, basename='vaccines')
router.register(r'vaccinations', PetVaccinationRecordViewSet, basename='vaccinations')

from .views import VaccinationViewSet, SystemVaccinationReminderViewSet, DewormingViewSet, SystemDewormingReminderViewSet
router.register(r'system-vaccinations', VaccinationViewSet, basename='system-vaccinations')
router.register(r'system-vaccination-reminders', SystemVaccinationReminderViewSet, basename='system-vaccination-reminders')
router.register(r'system-deworming', DewormingViewSet, basename='system-deworming')
router.register(r'system-deworming-reminders', SystemDewormingReminderViewSet, basename='system-deworming-reminders')


urlpatterns = [
    path('', include(router.urls)),
    path('entities/', dynamic_entity_list, name='dynamic-entities'),
    path('internal/create-online-appointment/', CreateOnlineAppointmentView.as_view(), name='create-online-appointment'),
]
