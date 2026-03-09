import os
import django
import sys

# Django setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import DashboardWidget, Capability

def seed():
    print("🌱 Seeding Dashboard Widgets...")
    
    # 1. Ensure Capabilities exist
    caps = [
        ('VETERINARY_VISITS', 'Medical Visits & Queues'),
        ('VETERINARY_VITALS', 'Patient Vitals Management'),
        ('VETERINARY_DOCTOR', 'Doctor Board & Consultations'),
        ('VETERINARY_LABS', 'Laboratory Orders'),
        ('VETERINARY_PHARMACY', 'Pharmacy & Prescriptions'),
        ('VETERINARY_MEDICINE_REMINDERS', 'Medication Reminders'),
        ('VETERINARY_ANALYTICS', 'Medical Analytics'),
        ('VETERINARY_SCHEDULE', 'Doctor Schedules'),
    ]
    
    cap_objs = {}
    for key, name in caps:
        obj, _ = Capability.objects.get_or_create(key=key, defaults={'label': name})
        cap_objs[key] = obj
        print(f"  - Cap: {key}")

    # 2. Seed Widgets
    widgets = [
        {
            'key': 'schedule',
            'label': 'Daily Schedule',
            'component_name': 'ScheduleWidget',
            'required': ['VETERINARY_SCHEDULE'],
            'order': 5
        },
        {
            'key': 'analytics',
            'label': 'Operational Analytics',
            'component_name': 'AnalyticsCards',
            'required': ['VETERINARY_ANALYTICS'],
            'order': 10
        },
        {
            'key': 'waiting-room',
            'label': 'Waiting Room',
            'component_name': 'WaitingRoomWidget',
            'required': ['VETERINARY_VISITS'],
            'order': 20
        },
        {
            'key': 'active-queue',
            'label': 'Active Consultations',
            'component_name': 'ActiveQueueWidget',
            'required': ['VETERINARY_DOCTOR'],
            'order': 30
        },
        {
            'key': 'vitals-queue',
            'label': 'Vitals Queue',
            'component_name': 'VitalsQueueWidget',
            'required': ['VETERINARY_VITALS'],
            'order': 40
        },
        {
            'key': 'lab-queue',
            'label': 'Lab Queue',
            'component_name': 'LabQueueWidget',
            'required': ['VETERINARY_LABS'],
            'order': 50
        },
        {
            'key': 'pharmacy-queue',
            'label': 'Pharmacy Queue',
            'component_name': 'PharmacyQueueWidget',
            'required': ['VETERINARY_PHARMACY'],
            'order': 60
        }
    ]

    for w in widgets:
        obj, created = DashboardWidget.objects.get_or_create(
            key=w['key'],
            defaults={
                'label': w['label'],
                'component_name': w['component_name'],
                'order': w['order'] if 'order' in w else 0,
                'is_active': True
            }
        )
        # Clear and set capabilities
        obj.required_capabilities.clear()
        for cap_key in w['required']:
            obj.required_capabilities.add(cap_objs[cap_key])
        
        print(f"  - {'Created' if created else 'Updated'} Widget: {w['key']}")

    print("✅ Seeding Complete.")

if __name__ == "__main__":
    seed()
