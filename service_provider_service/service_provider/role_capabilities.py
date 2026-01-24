
# [DEPRECATED] Role Default Capabilities Configuration
# This file is retained only for backward compatibility during migration.
# New logic relies on:
# 1. Providers: Plan (ProviderCapabilityAccess)
# 2. Employees: Plan ∩ Custom Role (ProviderRole)

# We only grant CORE access here to ensure basic system function.
DEFAULT_CORE_ACCESS = ["VETERINARY_CORE"]

def get_default_capabilities(role_name):
    """
    Returns the list of default capabilities for a given role name.
    Case-insensitive.
    
    NOTE: This is DEPRECATED for business logic. 
    It now returns only VETERINARY_CORE for all standard roles.
    Real permissions must come from the Plan or Custom Roles.
    """
    if not role_name:
        return []
    
    # Return CORE access for any valid role
    return DEFAULT_CORE_ACCESS
