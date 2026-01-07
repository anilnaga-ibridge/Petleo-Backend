
# Role Default Capabilities Configuration
# This defines the default capabilities for each role.
# These are intersected with the Organization's Plan Capabilities to determine final permissions.

ROLE_DEFAULT_CAPABILITIES = {
    "doctor": [
        "VETERINARY_CORE",
        "VETERINARY_PRESCRIPTIONS",
        "VETERINARY_VISITS", # Often needs to see the visit list
    ],
    "receptionist": [
        "VETERINARY_CORE",
        "VETERINARY_VISITS",
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
        "VETERINARY_MEDICINE_REMINDERS",
    ],
    "employee": [
        "VETERINARY_CORE", # Basic access, likely needs specific assignment
    ],
    "nurse": [
        "VETERINARY_CORE",
        "VETERINARY_VITALS",
        "VETERINARY_MEDICINE_REMINDERS", # Maybe?
    ]
}

ALL_VETERINARY_CAPABILITIES = [
    "VETERINARY_CORE",
    "VETERINARY_VISITS",
    "VETERINARY_VITALS",
    "VETERINARY_PRESCRIPTIONS",
    "VETERINARY_LABS",
    "VETERINARY_MEDICINE_REMINDERS",
]

def get_default_capabilities(role_name):
    """
    Returns the list of default capabilities for a given role name.
    Case-insensitive.
    """
    if not role_name:
        return []
    
    normalized_role = role_name.lower().strip()
    
    # Individual providers get ALL capabilities
    if normalized_role == "individual":
        return ALL_VETERINARY_CAPABILITIES

    return ROLE_DEFAULT_CAPABILITIES.get(normalized_role, [])
