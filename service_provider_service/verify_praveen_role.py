import os, django, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, VerifiedUser
from service_provider.views import get_my_permissions
from django.test import RequestFactory
from django.core.cache import cache

def verify_praveen():
    print(f"\n{'='*50}")
    print(f"🕵️  FINAL VERIFICATION FOR PRAVEEN")
    print(f"{'='*50}")
    
    # 1. Clear cache
    p = OrganizationEmployee.objects.filter(full_name__icontains='Praveen').first()
    if p:
        p.invalidate_permission_cache()
        print(f"✅ Cleared cache for {p.full_name}")
    
    # 2. Mock request
    user = VerifiedUser.objects.get(email='praveen@gmail.com')
    factory = RequestFactory()
    req = factory.get('/api/permissions/')
    req.user = user
    
    # 3. Call view
    res = get_my_permissions(req)
    
    profile = res.data.get('user_profile', {})
    print(f"\n📊 RESPONSE DATA:")
    print(f"Role: {profile.get('role')}")
    print(f"FullName: {profile.get('fullName')}")
    print(f"Email: {profile.get('email')}")
    
    # 4. Check capabilities
    perms = res.data.get('permissions', [])
    print(f"\n🛠️  CAPABILITIES COUNT: {len(perms)}")
    for svc in perms:
        print(f"Service: {svc.get('service_name')}")
        for cat in svc.get('categories', []):
             print(f"  - {cat.get('name')} | View={cat.get('can_view')}")

if __name__ == "__main__":
    verify_praveen()
