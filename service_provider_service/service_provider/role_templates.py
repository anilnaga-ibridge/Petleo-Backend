

def get_role_templates():
    """
    Returns the standard role templates and their associated feature definitions.
    Used by the frontend RoleManagementWizard to populate selections.
    """
    
    # 1. Define Veterinary Features (Granular Controls)
    # These map to the "Veterinary Management" section in the wizard.
    # The IDs here (e.g., 'vet_core') are used by the frontend to toggle groups of capabilities.
    veterinary_features = [
        {
            "id": "vet_core",
            "title": "Core Access",
            "description": "Dashboard access and basic pet search",
            "icon": "tabler-stethoscope",
            "capabilities": ["VETERINARY_CORE"]
        },
        {
            "id": "vet_visits",
            "title": "Visits & Queue",
            "description": "Manage OPD queue and patient visits",
            "icon": "tabler-calendar-time",
            "capabilities": ["VETERINARY_VISITS"]
        },
        {
            "id": "vet_doctor",
            "title": "Doctor Queue",
            "description": "Access active doctor consultation queue",
            "icon": "tabler-stethoscope",
            "capabilities": ["VETERINARY_DOCTOR"]
        },
        {
            "id": "vet_vitals",
            "title": "Vitals Recording",
            "description": "Record patient weight, temp, and vitals",
            "icon": "tabler-activity-heartbeat",
            "capabilities": ["VETERINARY_VITALS"]
        },
        {
            "id": "vet_prescriptions",
            "title": "Prescriptions",
            "description": "Create and manage digital prescriptions",
            "icon": "tabler-pill",
            "capabilities": ["VETERINARY_PRESCRIPTIONS"]
        },
        {
            "id": "vet_labs",
            "title": "Lab Orders",
            "description": "Order tests and view results",
            "icon": "tabler-microscope",
            "capabilities": ["VETERINARY_LABS"]
        },
        {
            "id": "vet_pharmacy",
            "title": "Pharmacy",
            "description": "Dispense medicines and manage inventory",
            "icon": "tabler-band-aid",
            "capabilities": ["VETERINARY_PHARMACY"]
        },
        {
            "id": "vet_medicine",
            "title": "Medicine Reminders",
            "description": "Set and track medicine schedules",
            "icon": "tabler-alarm",
            "capabilities": ["VETERINARY_MEDICINE_REMINDERS"]
        }
    ]

    # 2. Define Role Templates (Presets)
    # These allow one-click configuration of the above features.
    templates = [
        {
            "name": "Veterinary Doctor",
            "description": "Full medical access: Consultations, Rx, Labs",
            "services": ["VETERINARY_SERVICE"], 
            "features": ["vet_core", "vet_visits", "vet_doctor", "vet_vitals", "vet_prescriptions", "vet_labs"]
        },
        {
            "name": "Receptionist",
            "description": "Front desk: Manage queue and appointments",
            "services": ["VETERINARY_SERVICE"],
            "features": ["vet_core", "vet_visits"]
        },
        {
            "name": "Nurse",
            "description": "Medical support: Record vitals, manage visits, and medicine reminders",
            "services": ["VETERINARY_SERVICE"],
            "features": ["vet_core", "vet_visits", "vet_vitals", "vet_medicine"]
        },
        {
            "name": "Vitals Staff",
            "description": "Staff focused on recording patient vitals",
            "services": ["VETERINARY_SERVICE"],
            "features": ["vet_core", "vet_vitals"]
        },
        {
            "name": "Lab Technician",
            "description": "Lab staff: Manage test orders and results",
            "services": ["VETERINARY_SERVICE"],
            "features": ["vet_core", "vet_labs"]
        },
        {
            "name": "Pharmacy Staff",
            "description": "Manage prescriptions and reminders",
            "services": ["VETERINARY_SERVICE"],
            "features": ["vet_core", "vet_pharmacy", "vet_medicine"]
        }
    ]

    return {
        "templates": templates,
        "features": veterinary_features
    }
