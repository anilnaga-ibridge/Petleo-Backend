

def get_role_templates():
    """
    Returns the standard role templates and their associated feature definitions.
    Used by the frontend RoleManagementWizard to populate selections.
    """
    
    # 1. Define Veterinary Features (Granular Controls)
    veterinary_features = [
        {
            "id": "core_access",
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
            "id": "vet_doctor_station",
            "title": "Doctor Station",
            "description": "Access doctor consultation station",
            "icon": "tabler-stethoscope",
            "capabilities": ["VETERINARY_DOCTOR"]
        },
        {
            "id": "vet_patients",
            "title": "Patients",
            "description": "View and manage patient clinical records",
            "icon": "tabler-paw",
            "capabilities": ["VETERINARY_PATIENTS"]
        },
        {
            "id": "vet_vitals",
            "title": "Veterinary Assistant",
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
            "id": "vet_reminders",
            "title": "Medicine Reminders",
            "description": "Set and track medicine schedules",
            "icon": "tabler-alarm",
            "capabilities": ["VETERINARY_MEDICINE_REMINDERS"]
        },
        {
            "id": "vet_scheduling",
            "title": "Scheduling",
            "description": "Manage schedules, online and offline visits",
            "icon": "tabler-calendar-event",
            "capabilities": ["VETERINARY_SCHEDULE", "VETERINARY_ONLINE_CONSULT", "VETERINARY_OFFLINE_VISIT"]
        },
        {
            "id": "vet_system",
            "title": "System Management",
            "description": "Configure clinic settings and metadata",
            "icon": "tabler-settings",
            "capabilities": ["VETERINARY_ADMIN_SETTINGS", "VETERINARY_METADATA"]
        },
        {
            "id": "vet_checkout",
            "title": "Checkout & Billing",
            "description": "Finalize visits, process payments and billing",
            "icon": "tabler-cash-banknote",
            "capabilities": ["VETERINARY_CHECKOUT"]
        }
    ]

    # 2. Define Role Templates (Presets)
    templates = [
        {
            "name": "Practice Manager",
            "description": "Complete control over clinic operations and settings",
            "services": ["VETERINARY_SERVICE"],
            "features": ["core_access", "vet_visits", "vet_patients", "vet_vitals", "vet_doctor_station", "vet_prescriptions", "vet_labs", "vet_pharmacy", "vet_scheduling", "vet_system", "vet_checkout"]
        },
        {
            "name": "Veterinary Doctor",
            "description": "Full medical access: Consultations, Rx, Labs, and Scheduling",
            "services": ["VETERINARY_SERVICE"], 
            "features": ["core_access", "vet_visits", "vet_patients", "vet_vitals", "vet_doctor_station", "vet_prescriptions", "vet_labs", "vet_scheduling"]
        },
        {
            "name": "Receptionist",
            "description": "Front desk: Manage queue, visits and appointments",
            "services": ["VETERINARY_SERVICE"],
            "features": ["core_access", "vet_visits", "vet_patients", "vet_scheduling"]
        },
        {
            "name": "Nurse",
            "description": "Medical support: Record vitals, manage visits, and reminders",
            "services": ["VETERINARY_SERVICE"],
            "features": ["core_access", "vet_visits", "vet_patients", "vet_vitals", "vet_reminders"]
        },
        {
            "name": "Pharmacist",
            "description": "Manage prescriptions and pharmacy inventory",
            "services": ["VETERINARY_SERVICE"],
            "features": ["core_access", "vet_pharmacy"]
        },
        {
            "name": "Lab Technician",
            "description": "Lab staff: Manage test orders and results",
            "services": ["VETERINARY_SERVICE"],
            "features": ["core_access", "vet_labs"]
        }
    ]

    return {
        "templates": templates,
        "features": veterinary_features
    }
