import os
import django
import json
from django.db import transaction

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import (
    ProviderCapabilityAccess, 
    ProviderTemplateService, 
    ProviderTemplateCategory, 
    ProviderTemplateFacility, 
    ProviderTemplateFacility, 
    ProviderTemplatePricing
)
from service_provider.models import VerifiedUser, AllowedService

def manual_sync():
    print("--- Simulating Kafka Sync ---")
    
    email = 'nagaanil29@gmail.com'
    user = VerifiedUser.objects.filter(email=email).first()
    if not user:
        print(f"User {email} not found")
        return

    auth_user_id = user.auth_user_id
    print(f"User: {email} ({auth_user_id})")

    # Real Platinum Plan Payload
    payload = {
        "auth_user_id": auth_user_id,
        "purchased_plan": {
            "plan_id": "PLATINUM_PLAN_ID",
            "start_date": "2025-12-26T00:00:00Z",
            "end_date": "2026-12-26T00:00:00Z", # 1 Year validity
            "billing_cycle_id": "yearly"
        },
        "templates": {
          "services": [
            {
              "id": "711fac84-16dc-4252-b7e3-6afb7ee57c71",
              "name": "Grooming",
              "display_name": "Grooming",
              "icon": "tabler-scissors"
            },
            {
              "id": "2170653c-9de5-4f61-b1ca-35b1a0439b17",
              "name": "Day Care",
              "display_name": "Day Care",
              "icon": "tabler-heart-handshake"
            },
            {
              "id": "d0de4652-d2e7-4cab-ae09-05999f365eed",
              "name": "Trainning",
              "display_name": "Training",
              "icon": "tabler-school"
            }
          ],
          "categories": [
            {
              "id": "e3c49920-e626-4d3d-904d-e8dbe69cb3f6",
              "service_id": "711fac84-16dc-4252-b7e3-6afb7ee57c71",
              "name": "Nial Cutting"
            },
            {
              "id": "2e3ace4c-ed69-4be2-84e1-4a302ef1c411",
              "service_id": "2170653c-9de5-4f61-b1ca-35b1a0439b17",
              "name": "Small Breed Dog Day Care"
            },
            {
              "id": "999d6284-d8b5-4577-b000-1e51cc4ac5fa",
              "service_id": "711fac84-16dc-4252-b7e3-6afb7ee57c71",
              "name": "Hair Cut"
            },
            {
              "id": "33cc4bc5-6b26-4026-b702-ace53d0858db",
              "service_id": "d0de4652-d2e7-4cab-ae09-05999f365eed",
              "name": "Behavioral Training"
            }
          ],
          "facilities": [
            {
              "id": "9f6dfd37-7cba-4292-bbf1-efc14ed3c849",
              "category_id": "999d6284-d8b5-4577-b000-1e51cc4ac5fa",
              "name": "Hair Trimming & Styling",
              "description": "Hair Trimming & Styling"
            },
            {
              "id": "abd39092-5a5a-4816-a7cb-e2bf535c61c5",
              "category_id": "2e3ace4c-ed69-4be2-84e1-4a302ef1c411",
              "name": "Indoor Play Area",
              "description": "Indoor Play Area"
            },
            {
              "id": "95a3a4ce-b503-49e9-8531-d5b28e01a173",
              "category_id": "2e3ace4c-ed69-4be2-84e1-4a302ef1c411",
              "name": "Outdoor Play Area",
              "description": "Outdoor Play Area"
            },
            {
              "id": "c9954ea8-f1d1-44fb-9281-01e6d2856fba",
              "category_id": "33cc4bc5-6b26-4026-b702-ace53d0858db",
              "name": "Obedience Training Hall",
              "description": "Obedience Training Hall"
            }
          ],
          "pricing": [
            {
              "id": "b0391703-94b5-4203-9658-6a5bef34d66f",
              "service_id": "2170653c-9de5-4f61-b1ca-35b1a0439b17",
              "category_id": "2e9da8d4-9747-41a7-8bf4-96e4df658070",
              "facility_id": "abd39092-5a5a-4816-a7cb-e2bf535c61c5",
              "price": 9999.0,
              "duration": "per_hour"
            },
            {
              "id": "00fd90c3-c889-4ad0-9588-ff7219e7890e",
              "service_id": "711fac84-16dc-4252-b7e3-6afb7ee57c71",
              "category_id": "e3c49920-e626-4d3d-904d-e8dbe69cb3f6",
              "facility_id": "9f6dfd37-7cba-4292-bbf1-efc14ed3c849",
              "price": 899.0,
              "duration": "per_hour"
            },
            {
              "id": "2a20a45f-c617-42a9-95b2-253c457fae30",
              "service_id": "711fac84-16dc-4252-b7e3-6afb7ee57c71",
              "category_id": "999d6284-d8b5-4577-b000-1e51cc4ac5fa",
              "facility_id": "9f6dfd37-7cba-4292-bbf1-efc14ed3c849",
              "price": 899.0,
              "duration": "per_hour"
            },
            {
              "id": "10876803-948d-414a-b550-9b2699047df4",
              "service_id": "d0de4652-d2e7-4cab-ae09-05999f365eed",
              "category_id": "33cc4bc5-6b26-4026-b702-ace53d0858db",
              "facility_id": "c9954ea8-f1d1-44fb-9281-01e6d2856fba",
              "price": 897.0,
              "duration": "per_day"
            }
          ]
        },
        "permissions": [] # Empty explicit perms, relying on auto-gen
    }
    
    print("Processing payload...")
    
    # --- LOGIC COPIED FROM KAFKA CONSUMER ---
    try:
        with transaction.atomic():
            templates = payload["templates"]
            
            # 1. SYNC TEMPLATES
            print("Syncing Services...")
            for svc in templates.get("services", []):
                print(f" - Service: {svc['name']} ({svc['id']})")
                ProviderTemplateService.objects.update_or_create(
                    super_admin_service_id=svc["id"],
                    defaults={"name": svc["name"], "display_name": svc["display_name"], "icon": svc.get("icon")}
                )
            
            print("Syncing Categories...")
            for cat in templates.get("categories", []):
                print(f" - Category: {cat['name']} ({cat['id']}) -> Service: {cat['service_id']}")
                try:
                    svc_obj = ProviderTemplateService.objects.get(super_admin_service_id=cat["service_id"])
                    ProviderTemplateCategory.objects.update_or_create(
                        super_admin_category_id=cat["id"],
                        defaults={"service": svc_obj, "name": cat["name"]}
                    )
                except ProviderTemplateService.DoesNotExist:
                    print(f"❌ Service {cat['service_id']} not found for category {cat['name']}")
                    raise

            print("Syncing Facilities...")
            for fac in templates.get("facilities", []):
                print(f" - Facility: {fac['name']} ({fac['id']}) -> Category: {fac['category_id']}")
                try:
                    cat_obj = ProviderTemplateCategory.objects.get(super_admin_category_id=fac["category_id"])
                    ProviderTemplateFacility.objects.update_or_create(
                        super_admin_facility_id=fac["id"],
                        defaults={"category": cat_obj, "name": fac["name"], "description": fac.get("description")}
                    )
                except ProviderTemplateCategory.DoesNotExist:
                    print(f"❌ Category {fac['category_id']} not found for facility {fac['name']}")
                    # List all categories to debug
                    all_cats = ProviderTemplateCategory.objects.values_list('super_admin_category_id', flat=True)
                    print(f"   Available Categories: {list(all_cats)}")
                    raise

            print("Syncing Pricing...")
            for price in templates.get("pricing", []):
                try:
                    svc_obj = ProviderTemplateService.objects.get(super_admin_service_id=price["service_id"])
                    
                    cat_obj = None
                    if price.get("category_id"):
                        try:
                            cat_obj = ProviderTemplateCategory.objects.get(super_admin_category_id=price["category_id"])
                        except ProviderTemplateCategory.DoesNotExist:
                            print(f"⚠️ Skipping Pricing {price['id']}: Category {price['category_id']} not found")
                            continue

                    fac_obj = None
                    if price.get("facility_id"):
                        try:
                            fac_obj = ProviderTemplateFacility.objects.get(super_admin_facility_id=price["facility_id"])
                        except ProviderTemplateFacility.DoesNotExist:
                             print(f"⚠️ Skipping Pricing {price['id']}: Facility {price['facility_id']} not found")
                             continue
                    
                    ProviderTemplatePricing.objects.update_or_create(
                        super_admin_pricing_id=price["id"],
                        defaults={
                            "service": svc_obj, "category": cat_obj, "facility": fac_obj,
                            "price": price["price"], "duration": price["duration"]
                        }
                    )
                except Exception as e:
                    print(f"⚠️ Error syncing pricing {price['id']}: {e}")
                    continue
                
            print("✅ Templates Synced")

            # 2. SYNC PERMISSIONS
            plan_id = payload.get("purchased_plan", {}).get("plan_id")
            ProviderCapabilityAccess.objects.filter(user=user).delete() # Clear all for test
            
            perms_map = {}
            def add_perm(s_id, c_id, f_id, p_id):
                key = (s_id, c_id, f_id, p_id)
                if key not in perms_map:
                    perms_map[key] = {
                        "service_id": s_id, "category_id": c_id, "facility_id": f_id, "pricing_id": p_id,
                        "can_view": True, "can_create": False, "can_edit": False, "can_delete": False
                    }

            # Auto-gen
            for svc in templates.get("services", []): add_perm(svc["id"], None, None, None)
            
            cat_svc_map = {c["id"]: c["service_id"] for c in templates.get("categories", [])}
            for cat in templates.get("categories", []): add_perm(cat["service_id"], cat["id"], None, None)
            
            for fac in templates.get("facilities", []):
                s_id = cat_svc_map.get(fac["category_id"])
                if s_id: add_perm(s_id, fac["category_id"], fac["id"], None)
                
            for price in templates.get("pricing", []):
                add_perm(price["service_id"], price.get("category_id"), price.get("facility_id"), price["id"])

            # Create Objects
            new_perms = []
            for p in perms_map.values():
                new_perms.append(ProviderCapabilityAccess(
                    user=user, plan_id=plan_id,
                    service_id=p["service_id"], category_id=p["category_id"],
                    facility_id=p["facility_id"], pricing_id=p["pricing_id"],
                    can_view=p["can_view"], can_create=p["can_create"],
                    can_edit=p["can_edit"], can_delete=p["can_delete"]
                ))
            
            ProviderCapabilityAccess.objects.bulk_create(new_perms)
            print(f"✅ Permissions Synced: {len(new_perms)} records created")

            # 3. SYNC SUBSCRIPTION
            print("Syncing Subscription...")
            purchased_plan_info = payload.get("purchased_plan", {})
            if purchased_plan_info:
                from service_provider.models import ProviderSubscription
                from django.utils.dateparse import parse_datetime
                from django.utils import timezone
                
                start_date = parse_datetime(purchased_plan_info.get("start_date"))
                end_date = parse_datetime(purchased_plan_info.get("end_date"))
                
                is_active = True
                if end_date and end_date < timezone.now():
                    is_active = False
                    
                ProviderSubscription.objects.update_or_create(
                    verified_user=user,
                    defaults={
                        "plan_id": purchased_plan_info["plan_id"],
                        "billing_cycle_id": purchased_plan_info.get("billing_cycle_id"),
                        "start_date": start_date,
                        "end_date": end_date,
                        "is_active": is_active
                    }
                )
                print(f"✅ Subscription Synced (Active: {is_active})")

            # 4. SYNC ALLOWED SERVICES (High-level)
            print("Syncing Allowed Services...")
            
            # Clear existing
            AllowedService.objects.filter(verified_user=user).delete()
            
            # Re-create based on templates
            allowed_services = []
            for svc in payload.get("templates", {}).get("services", []):
                allowed_services.append(AllowedService(
                    verified_user=user,
                    service_id=svc["id"],
                    name=svc["display_name"],
                    icon=svc.get("icon", "tabler-box")
                ))
            
            if allowed_services:
                AllowedService.objects.bulk_create(allowed_services)
                print(f"✅ Allowed Services Synced: {len(allowed_services)} records")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    manual_sync()
