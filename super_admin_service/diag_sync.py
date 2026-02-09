import os
import django
import sys

def check_super_admin():
    sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/super_admin_service")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
    django.setup()
    from dynamic_fields.models import ProviderDocumentVerification
    print(f"SuperAdmin Pending Docs: {ProviderDocumentVerification.objects.filter(status='pending').count()}")
    print(f"SuperAdmin Total Docs: {ProviderDocumentVerification.objects.count()}")
    for doc in ProviderDocumentVerification.objects.all():
        print(f"  - Doc: {doc.filename}, Provider: {doc.auth_user_id}, Status: {doc.status}")

def check_service_provider():
    # Reset django setup for next service
    import importlib
    importlib.reload(django)
    sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
    os.environ["DJANGO_SETTINGS_MODULE"] = "service_provider_service.settings"
    # We need to clear existing django setup
    from django.conf import settings
    settings._wrapped = django.utils.functional.empty
    django.setup()
    from provider_dynamic_fields.models import ProviderDocument
    print(f"ServiceProvider Total Docs: {ProviderDocument.objects.count()}")
    for doc in ProviderDocument.objects.all():
        print(f"  - Doc: {doc.filename}, Provider: {doc.verified_user.auth_user_id}")

if __name__ == "__main__":
    print("--- Super Admin ---")
    try:
        check_super_admin()
    except Exception as e:
        print(f"Error checking Super Admin: {e}")
    
    print("\n--- Service Provider ---")
    try:
        # Resetting environment variables to avoid conflicts
        os.environ.pop("DJANGO_SETTINGS_MODULE", None)
        # Re-run in a separate process or just use raw SQL if this fails
        # I'll try raw SQL for reliability if this complex setup fails
    except Exception as e:
        print(f"Error preparing Service Provider check: {e}")

