

def get_role_templates():
    """
    Returns the standard role templates and their associated feature definitions.
    Used by the frontend RoleManagementWizard to populate selections.
    """
    
    # Standard Permission Profiles
    READ_ONLY = {"can_view": True, "can_create": False, "can_edit": False, "can_delete": False}
    FULL_ACCESS = {"can_view": True, "can_create": True, "can_edit": True, "can_delete": True}
    STAFF_STANDARD = {"can_view": True, "can_create": True, "can_edit": True, "can_delete": False}

    # 1. Define Veterinary Features (Granular Controls)
    veterinary_features = [
        {
            "id": "core_access",
            "title": "Core Access",
            "description": "Dashboard access and basic pet search",
            "icon": "tabler-stethoscope",
            "capabilities": ["VETERINARY_CORE"],
            "granular": True,
            "default_permissions": FULL_ACCESS
        },
        {
            "id": "vet_visits",
            "title": "Visits & Queue",
            "description": "Manage OPD queue and patient visits",
            "icon": "tabler-calendar-time",
            "capabilities": ["VETERINARY_VISITS"],
            "granular": True,
            "default_permissions": READ_ONLY # Default to view-only for safety
        },
        {
            "id": "vet_doctor_station",
            "title": "Doctor Station",
            "description": "Access doctor consultation station",
            "icon": "tabler-stethoscope",
            "capabilities": ["VETERINARY_DOCTOR"],
            "granular": True,
            "default_permissions": READ_ONLY
        },
        {
            "id": "vet_patients",
            "title": "Patients",
            "description": "View and manage patient clinical records",
            "icon": "tabler-paw",
            "capabilities": ["VETERINARY_PATIENTS"],
            "granular": True,
            "default_permissions": READ_ONLY
        },
        {
            "id": "vet_vitals",
            "title": "Veterinary Assistant",
            "description": "Record patient weight, temp, and vitals",
            "icon": "tabler-activity-heartbeat",
            "capabilities": ["VETERINARY_VITALS"],
            "granular": True,
            "default_permissions": READ_ONLY
        },
        {
            "id": "vet_prescriptions",
            "title": "Prescriptions",
            "description": "Create and manage digital prescriptions",
            "icon": "tabler-pill",
            "capabilities": ["VETERINARY_PRESCRIPTIONS"],
            "granular": True,
            "default_permissions": READ_ONLY
        },
        {
            "id": "vet_labs",
            "title": "Lab Orders",
            "description": "Order tests and view results",
            "icon": "tabler-microscope",
            "capabilities": ["VETERINARY_LABS"],
            "granular": True,
            "default_permissions": READ_ONLY
        },
        {
            "id": "vet_pharmacy",
            "title": "Pharmacy",
            "description": "Dispense medicines and manage prescriptions",
            "icon": "tabler-band-aid",
            "capabilities": ["VETERINARY_PHARMACY"],
            "granular": True,
            "default_permissions": READ_ONLY
        },
        {
            "id": "vet_pharmacy_store",
            "title": "Pharmacy Store",
            "description": "Inventory control, batch tracking, and stock alerts",
            "icon": "tabler-building-warehouse",
            "capabilities": ["VETERINARY_PHARMACY_STORE"],
            "granular": True,
            "default_permissions": READ_ONLY
        },
        {
            "id": "vet_reminders",
            "title": "Medicine Reminders",
            "description": "Set and track medicine schedules",
            "icon": "tabler-alarm",
            "capabilities": ["VETERINARY_MEDICINE_REMINDERS"],
            "granular": True,
            "default_permissions": READ_ONLY
        },
        {
            "id": "vet_scheduling",
            "title": "Scheduling",
            "description": "Manage doctor schedules and availability",
            "icon": "tabler-calendar-event",
            "capabilities": ["VETERINARY_SCHEDULE"],
            "granular": True,
            "default_permissions": READ_ONLY
        },
        {
            "id": "vet_online_consult",
            "title": "Online Consultancy",
            "description": "Manage virtual consultations and video meetings",
            "icon": "tabler-video",
            "capabilities": ["VETERINARY_ONLINE_CONSULT"],
            "granular": True,
            "default_permissions": READ_ONLY
        },
        {
            "id": "vet_offline_visit",
            "title": "Offline Visits",
            "description": "Manage physical walk-in appointments",
            "icon": "tabler-building-hospital",
            "capabilities": ["VETERINARY_OFFLINE_VISIT"],
            "granular": True,
            "default_permissions": READ_ONLY
        },
        {
            "id": "vet_system",
            "title": "System Management",
            "description": "Configure clinic settings and metadata",
            "icon": "tabler-settings",
            "capabilities": ["VETERINARY_ADMIN_SETTINGS", "VETERINARY_METADATA"],
            "granular": True,
            "default_permissions": READ_ONLY
        },
        {
            "id": "sys_employees",
            "title": "Employee Management",
            "description": "Manage staff profiles and assignments",
            "icon": "tabler-users",
            "capabilities": ["EMPLOYEE_MANAGEMENT"],
            "granular": True,
            "default_permissions": READ_ONLY
        },
        {
            "id": "sys_roles",
            "title": "Role Management",
            "description": "Configure roles and access permissions",
            "icon": "tabler-shield-lock",
            "capabilities": ["ROLE_MANAGEMENT"],
            "granular": True,
            "default_permissions": READ_ONLY
        },
        {
            "id": "sys_bookings",
            "title": "Customer Booking Management",
            "description": "Manage online/offline customer bookings",
            "icon": "tabler-calendar-heart",
            "capabilities": ["CUSTOMER_BOOKING"],
            "granular": True,
            "default_permissions": READ_ONLY
        },
        {
            "id": "sys_clinic",
            "title": "Clinic Management",
            "description": "Configure clinic settings and opening hours",
            "icon": "tabler-building",
            "capabilities": ["CLINIC_MANAGEMENT"],
            "granular": True,
            "default_permissions": READ_ONLY
        }
    ]

    # 2. Define Role Templates (Presets)
    templates = [
        {
            "name": "Practice Manager",
            "description": "Complete control over clinic operations and settings",
            "services": ["VETERINARY_SERVICE"],
            "features": ["core_access", "vet_visits", "vet_patients", "vet_vitals", "vet_doctor_station", "vet_prescriptions", "vet_labs", "vet_pharmacy", "vet_pharmacy_store", "vet_scheduling", "vet_online_consult", "vet_offline_visit", "vet_system", "vet_checkout"],
            "overrides": {
                # Practice Managers get full access to everything
                f: FULL_ACCESS for f in ["vet_visits", "vet_patients", "vet_vitals", "vet_doctor_station", "vet_prescriptions", "vet_labs", "vet_pharmacy", "vet_pharmacy_store", "vet_scheduling", "vet_online_consult", "vet_offline_visit", "vet_system", "vet_checkout", "core_access"]
            }
        },
        {
            "name": "Veterinary Doctor",
            "description": "Full medical access: Consultations, Rx, Labs, and Scheduling",
            "services": ["VETERINARY_SERVICE"], 
            "features": ["core_access", "vet_visits", "vet_patients", "vet_vitals", "vet_doctor_station", "vet_prescriptions", "vet_labs", "vet_scheduling", "vet_online_consult"],
            "overrides": {
                # Doctors get standard staff access (Create/Edit but no Delete for records)
                f: STAFF_STANDARD for f in ["vet_visits", "vet_patients", "vet_vitals", "vet_doctor_station", "vet_prescriptions", "vet_labs", "vet_scheduling", "vet_online_consult"]
            }
        },
        {
            "name": "Receptionist",
            "description": "Front desk: Manage queue, visits and appointments",
            "services": ["VETERINARY_SERVICE"],
            "features": ["core_access", "vet_visits", "vet_patients", "vet_scheduling", "vet_offline_visit"],
            "overrides": {
                # 🤖 AUTOMATIC: Clinical modules now default to READ_ONLY for Receptionists
                # We only need to override if we want to GRANT more than view-only.
            }
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
            "features": ["core_access", "vet_pharmacy", "vet_pharmacy_store"]
        },
        {
            "id": "lab_tech",
            "name": "Lab Technician",
            "description": "Lab staff: Manage test orders and results",
            "services": ["VETERINARY_SERVICE"],
            "features": ["core_access", "vet_labs"]
        },
        {
            "id": "sys_admin",
            "name": "System Administrator",
            "description": "Global administrator: Manage employees, roles, bookings, and clinic settings",
            "services": ["SYSTEM_ADMIN"],
            "features": ["sys_employees", "sys_roles", "sys_bookings", "sys_clinic"]
        }
    ]

    return {
        "templates": templates,
        "features": veterinary_features
    }
