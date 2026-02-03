# facility_mapping_test.py

import copy

templates = {
    "services": [{"id": "s1", "name": "Grooming"}],
    "categories": [
        {"id": "c1", "service_id": "s1", "name": "Hair Cut"},
        {"id": "c2", "service_id": "s1", "name": "Bath"}
    ],
    "facilities": []
}

# Mock Facilities from DB (Super Admin)
# Facility F1 belongs to Service S1
all_facs = [{"id": "f1", "service_id": "s1", "name": "Deluxe Suite"}]

print("--- Current Publisher Logic ---")
seen_facilities = set()
service_to_cat_map = {"s1": ["c1", "c2"]}

for fac in all_facs:
    s_id = fac["service_id"]
    cats = service_to_cat_map.get(s_id, [])
    
    if not cats: continue
        
    # LOGIC FLAW: Takes only the first category
    target_cat_id = cats[0] 
    
    if fac["id"] not in seen_facilities:
        templates["facilities"].append({
            "id": fac["id"],
            "category_id": target_cat_id,
            "name": fac["name"]
        })
        seen_facilities.add(fac["id"])

print("Facilities Payload:", templates["facilities"])
print("Notice that 'Deluxe Suite' is ONLY in 'Hair Cut' (c1). It is missing from 'Bath' (c2).")

print("\n--- Proposed Fix (Multi-Category) ---")
templates["facilities"] = []
seen_facilities = set() # Reset

for fac in all_facs:
    s_id = fac["service_id"]
    cats = service_to_cat_map.get(s_id, [])
    
    if not cats: continue
        
    # FIX: Add for ALL categories? Or ask requirements?
    # Usually a facility like "Room" is physical and exists regardless of category.
    # checking the ProviderTemplateFacility model, it requires a generic category.
    
    for cat_id in cats:
        # We need unique ID for the template facility if we duplicate it?
        # ProviderTemplateFacility has super_admin_facility_id unique=True constraint?
        # Let's check models.py of Provider Service again.
        pass

print("...Checking Provider constraints...")
