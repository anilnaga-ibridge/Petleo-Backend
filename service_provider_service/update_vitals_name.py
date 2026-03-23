import os
import django

# Setup path based on current directory
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import FeatureModule

def run():
    print("Updating FeatureModules...")
    count = FeatureModule.objects.filter(name='Vitals').update(name='Veterinary Assistant')
    print(f"Update complete. {count} records modified.")

if __name__ == "__main__":
    run()
