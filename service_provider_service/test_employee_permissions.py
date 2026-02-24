#!/usr/bin/env python
"""
Employee Permission Verification Script
Tests that employee permissions are correctly filtered by role capabilities
"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, ProviderRole
from service_provider.utils import _build_permission_tree

def test_employee_permissions(email):
    """Test permissions for a specific employee"""
    print(f"\n{'='*80}")
    print(f"Testing Employee: {email}")
    print(f"{'='*80}\n")
    
    try:
        employee = OrganizationEmployee.objects.get(email=email)
    except OrganizationEmployee.DoesNotExist:
        print(f"❌ Employee not found: {email}")
        return
    
    print(f"✅ Employee Found:")
    print(f"   Name: {employee.full_name}")
    print(f"   Role: {employee.provider_role.name if employee.provider_role else 'No role assigned'}")
    print(f"   Status: {employee.status}")
    
    if not employee.provider_role:
        print(f"\n⚠️ No role assigned - employee will have no permissions")
        return
    
    # Get role capabilities
    role_caps = list(employee.provider_role.capabilities.values_list('capability_key', flat=True))
    print(f"\n📋 Role Capabilities ({len(role_caps)}):")
    for cap in sorted(role_caps):
        print(f"   - {cap}")
    
    # Get organization (subscription owner)
    org = employee.organization
    print(f"\n🏢 Organization: {org.verified_user.email}")
    
    # Get organization's plan capabilities
    org_caps = org.verified_user.get_all_plan_capabilities()
    print(f"\n📦 Organization Plan Capabilities ({len(org_caps)}):")
    for cap in sorted(org_caps):
        print(f"   - {cap}")
    
    # Calculate final permissions (intersection)
    final_perms = employee.get_final_permissions()
    print(f"\n🎯 Final Employee Permissions ({len(final_perms)}):")
    print(f"   (Organization Plan ∩ Employee Role)")
    for perm in sorted(final_perms):
        print(f"   - {perm}")
    
    # Build permission tree (what the API returns)
    tree = _build_permission_tree(org.verified_user)
    print(f"\n🌲 Organization Permission Tree ({len(tree)} services):")
    for service in tree:
        print(f"   - {service.get('service_name')} ({service.get('service_key')})")
        print(f"     Categories: {len(service.get('categories', []))}")
    
    # Simulate the filtering that happens in get_my_permissions
    print(f"\n🔍 Simulating Employee Filtering...")
    filtered_tree = []
    
    for service in tree:
        service_key = service.get('service_key')
        
        if service_key in final_perms:
            # Filter categories
            filtered_categories = []
            for category in service.get('categories', []):
                cat_key = category.get('linked_capability') or category.get('category_key')
                if cat_key and cat_key in final_perms:
                    filtered_categories.append(category)
            
            filtered_service = service.copy()
            filtered_service['categories'] = filtered_categories
            filtered_tree.append(filtered_service)
        else:
            # Check if any categories match
            filtered_categories = []
            for category in service.get('categories', []):
                cat_key = category.get('linked_capability') or category.get('category_key')
                if cat_key and cat_key in final_perms:
                    filtered_categories.append(category)
            
            if filtered_categories:
                filtered_service = service.copy()
                filtered_service['categories'] = filtered_categories
                filtered_tree.append(filtered_service)
    
    print(f"\n✅ Filtered Tree ({len(filtered_tree)} services):")
    for service in filtered_tree:
        print(f"\n   📦 {service.get('service_name')} ({service.get('service_key')})")
        print(f"      Categories ({len(service.get('categories', []))}):")
        for cat in service.get('categories', []):
            print(f"         - {cat.get('name')} ({cat.get('linked_capability')})")
    
    print(f"\n{'='*80}")
    print(f"✅ Test Complete for {email}")
    print(f"{'='*80}\n")

def test_all_employees():
    """Test all active employees"""
    employees = OrganizationEmployee.objects.filter(status='ACTIVE').select_related('provider_role')
    
    print(f"\n{'='*80}")
    print(f"Testing All Active Employees ({employees.count()})")
    print(f"{'='*80}")
    
    for emp in employees:
        test_employee_permissions(emp.email)
        print("\n")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # Test specific employee
        email = sys.argv[1]
        test_employee_permissions(email)
    else:
        # Test all employees
        test_all_employees()
