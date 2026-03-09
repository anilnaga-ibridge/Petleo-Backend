import json

assignments = [
    {"staff_auth_id": "fake-rahul-id-1234", "clinic_name": "Clinic - Anil Naga"},
    {"staff_auth_id": "0bff4c7a-40cf-4471-aab1-9d036da2e0ec", "clinic_name": "Clinic - Anil Naga"},
    {"staff_auth_id": "709c36e6-69fc-4c58-b639-42f7bea302a5", "clinic_name": "Clinic - Anil Naga"}
]

employees = [
    {"auth_user_id": "fake-rahul-id-1234", "full_name": "Rahul Test"},
    {"auth_user_id": "709c36e6-69fc-4c58-b639-42f7bea302a5", "full_name": "Naga"}
]

result = []
for emp in employees:
    staffAssignments = [a for a in assignments if a["staff_auth_id"] == emp["auth_user_id"]]
    emp_data = {
        **emp,
        "assigned_clinics": [a.get("clinic_name") or a.get("clinic") for a in staffAssignments]
    }
    result.append(emp_data)

print(json.dumps(result, indent=2))
