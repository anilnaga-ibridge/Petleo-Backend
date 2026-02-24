import os
import django
import sys
import json

# Set up Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider, VerifiedUser
from service_provider.serializers import PublicProviderProfileSerializer

def verify_serializer_output(email="anil.naga@ibridge.digital"):
    print(f"\n{'='*100}")
    print(f"{'SERIALIZER OUTPUT VERIFICATION':^100}")
    print(f"{'='*100}\n")
    
    try:
        user = VerifiedUser.objects.get(email=email)
        provider = ServiceProvider.objects.get(verified_user=user)
        
        serializer = PublicProviderProfileSerializer(provider)
        data = serializer.data
        
        print(f"🏥 Provider: {data.get('providerName')} ({email})")
        print(f"📍 Location: '{data.get('location')}'")
        print(f"📧 Email: {data.get('email')}")
        
        # Check if address is also present
        print(f"🏠 Address: '{data.get('address')}'")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    verify_serializer_output()
