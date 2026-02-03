# duplicate_perm_test.py

perm_map = {}

def add_perm(s_id, c_id, f_id, p_id):
    key = (s_id, c_id, f_id, p_id)
    if key not in perm_map:
        perm_map[key] = {
            "service": s_id,
            "category": c_id,
            "facility": f_id,
            "pricing": p_id
        }
    print(f"Added: {key}")

# Mock Data
facilities = [{"id": "fac1", "category_id": "cat1", "service_id": "srv1"}]
pricing = [{"id": "price1", "facility_id": "fac1", "category_id": "cat1", "service_id": "srv1"}]

print("--- Current Logic ---")
# Current Logic
# 1. Facilities
for fac in facilities:
    add_perm(fac["service_id"], fac["category_id"], fac["id"], None)

# 2. Pricing
for price in pricing:
    add_perm(price["service_id"], price["category_id"], price["facility_id"], price["id"])

print("\nResult keys:", list(perm_map.keys()))

print("\n--- Proposed Fix ---")
perm_map = {} # Reset

# 1. Facilities
for fac in facilities:
    add_perm(fac["service_id"], fac["category_id"], fac["id"], None)

# 2. Pricing
for price in pricing:
    # CHECK AND REMOVE PLACEHOLDER
    placeholder_key = (price["service_id"], price["category_id"], price["facility_id"], None)
    if placeholder_key in perm_map:
        print(f"Removing placeholder: {placeholder_key}")
        del perm_map[placeholder_key]
        
    add_perm(price["service_id"], price["category_id"], price["facility_id"], price["id"])

print("\nResult keys:", list(perm_map.keys()))
