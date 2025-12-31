
# Role Default Capabilities Configuration
# This defines the default capabilities for each role.
# These are intersected with the Organization's Plan Capabilities to determine final permissions.

ROLE_DEFAULT_CAPABILITIES = {
    "doctor": [
        "VETERINARY_CORE",
        "VETERINARY_VISITS",
        "VETERINARY_PRESCRIPTIONS",
        "VETERINARY_LABS",
        "VETERINARY_ONLINE_CONSULT",
        "VETERINARY_OFFLINE_VISIT",
        "VETERINARY_MEDICINE_REMINDERS",
        "VETERINARY_SCHEDULE",
    ],
    "receptionist": [
        "VETERINARY_CORE",
        "VETERINARY_SCHEDULE",
        "VETERINARY_VISITS", # Can view/manage visits but maybe restricted actions (handled by granular perms if needed)
        "VETERINARY_OFFLINE_VISIT",
    ],
    "vitals staff": [
        "VETERINARY_CORE",
        "VETERINARY_VITALS",
    ],
    "vitalsstaff": [ # Alias
        "VETERINARY_CORE",
        "VETERINARY_VITALS",
    ],
    "lab tech": [
        "VETERINARY_CORE",
        "VETERINARY_LABS",
    ],
    "labtech": [ # Alias
        "VETERINARY_CORE",
        "VETERINARY_LABS",
    ],
    "pharmacy": [
        "VETERINARY_CORE",
        "VETERINARY_PRESCRIPTIONS", # Can view prescriptions to dispense
        "VETERINARY_MEDICINE_REMINDERS",
    ],
    "employee": [
        "VETERINARY_CORE", # Basic access
    ],
    # Add new roles here as needed
    "nurse": [
        "VETERINARY_CORE",
        "VETERINARY_VITALS",
        "VETERINARY_MEDICINE_REMINDERS",
    ]
}

def get_default_capabilities(role_name):
    """
    Returns the list of default capabilities for a given role name.
    Case-insensitive.
    """
    if not role_name:
        return []
    
    normalized_role = role_name.lower().strip()
    return ROLE_DEFAULT_CAPABILITIES.get(normalized_role, [])
