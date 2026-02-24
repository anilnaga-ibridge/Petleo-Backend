import os
import django
import sys

# Set up Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/customer_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
django.setup()

from pets.views import PetViewSet
from pets.serializers import PetSerializer, PetListSerializer

def verify_pet_viewset():
    print(f"\n{'='*100}")
    print(f"{'PET VIEWSET VERIFICATION':^100}")
    print(f"{'='*100}\n")
    
    viewset = PetViewSet()
    
    # Test list action
    viewset.action = 'list'
    serializer_class = viewset.get_serializer_class()
    print(f"📋 Action 'list' -> Serializer: {serializer_class.__name__}")
    assert serializer_class == PetListSerializer
    
    # Test create action (The one that was failing)
    viewset.action = 'create'
    serializer_class = viewset.get_serializer_class()
    print(f"➕ Action 'create' -> Serializer: {serializer_class.__name__}")
    assert serializer_class == PetSerializer
    
    print("\n✅ PetViewSet verification PASSED!")

if __name__ == "__main__":
    verify_pet_viewset()
