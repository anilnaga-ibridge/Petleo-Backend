
import os
import django
import sys

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/super_admin_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from plans_coupens.models import Plan

print(f"Total Plans: {Plan.objects.count()}")
for p in Plan.objects.all():
    print(f"Plan: {p.title} (ID: {p.id}, Price: {p.price})")
