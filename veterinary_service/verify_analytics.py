import os
import django
import datetime
import json
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from veterinary.models import Visit, Clinic
from veterinary.services import ClinicAnalyticsService

# Ensure we have a clinic
try:
    clinic = Clinic.objects.first()
    if not clinic:
        print("No clinic found! Create one first.")
        exit(1)

    print(f"Testing Analytics for Clinic: {clinic.name} ({clinic.id})")
    today = timezone.now().date()
    print(f"Target Date: {today}")

    metrics = ClinicAnalyticsService.get_dashboard_metrics(clinic.id, str(today))

    print("\n--- EXECUTIVE DASHBOARD ---")
    print(json.dumps(metrics['executive'], indent=2))

    print("\n--- RECEPTION ---")
    print(json.dumps(metrics['reception'], indent=2))

    print("\n--- VITALS ---")
    print(json.dumps(metrics['vitals'], indent=2))

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
