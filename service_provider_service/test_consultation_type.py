import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ConsultationType, ServiceProvider

print("Total Consultation Types: ", ConsultationType.objects.count())

for ct in ConsultationType.objects.all()[:5]:
    print(ct.id, " - ", ct.name, " - ", ct.consultation_fee, " - Provider: ", ct.provider.id)

