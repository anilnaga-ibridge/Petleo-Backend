
import requests
import uuid

BASE_URL = "http://localhost:8004/api/v1"

def test_dynamic_fields():
    print("🧪 Testing Dynamic Field CRUD...")
    # 1. Get first clinic
    res = requests.get(f"{BASE_URL}/clinics/")
    clinic_id = res.json()[0]['id']
    
    # 2. Create Field
    new_field = {
        "clinic": clinic_id,
        "entity_type": "PET",
        "key": f"test_field_{uuid.uuid4().hex[:4]}",
        "label": "Test Field",
        "field_type": "TEXT",
        "is_required": False
    }
    res = requests.post(f"{BASE_URL}/field-definitions/", json=new_field)
    assert res.status_code == 201
    field_id = res.json()['id']
    print(f"✅ Created Field: {field_id}")
    
    # 3. Update Field
    res = requests.put(f"{BASE_URL}/field-definitions/{field_id}/", json={**new_field, "label": "Updated Label"})
    assert res.status_code == 200
    assert res.json()['label'] == "Updated Label"
    print(f"✅ Updated Field: {field_id}")
    
    # 4. Delete Field
    res = requests.delete(f"{BASE_URL}/field-definitions/{field_id}/")
    assert res.status_code == 204
    print(f"✅ Deleted Field: {field_id}")

def test_form_definitions():
    print("\n🧪 Testing Form Definition CRUD...")
    # 1. Create Form
    new_form = {
        "code": f"TEST_FORM_{uuid.uuid4().hex[:4]}",
        "name": "Test Form",
        "fields": [
            {"field_key": "temp", "label": "Temperature", "field_type": "NUMBER"}
        ]
    }
    res = requests.post(f"{BASE_URL}/forms/definitions/", json=new_form)
    assert res.status_code == 201
    form_code = res.json()['code']
    print(f"✅ Created Form: {form_code}")
    
    # 2. Update Form (Add a field)
    updated_form = {
        "name": "Updated Test Form",
        "fields": [
            {"field_key": "temp", "label": "Temperature", "field_type": "NUMBER"},
            {"field_key": "weight", "label": "Weight", "field_type": "NUMBER"}
        ]
    }
    res = requests.put(f"{BASE_URL}/forms/definitions/{form_code}/", json=updated_form)
    assert res.status_code == 200
    assert len(res.json()['fields']) == 2
    print(f"✅ Updated Form: {form_code} (Added field)")
    
    # 3. Delete Form
    res = requests.delete(f"{BASE_URL}/forms/definitions/{form_code}/")
    assert res.status_code == 204
    print(f"✅ Deleted Form: {form_code}")

if __name__ == "__main__":
    try:
        test_dynamic_fields()
        test_form_definitions()
        print("\n✨ All API verifications passed!")
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
