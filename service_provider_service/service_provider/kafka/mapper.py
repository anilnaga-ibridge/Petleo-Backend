from typing import Dict, Any
from .schemas import PermissionFlags, CapabilityPayload

class PermissionMapper:
    """
    Business logic layer for mapping Super Admin JSON permissions 
    to Provider Service flat DB columns.
    """
    
    @staticmethod
    def map_to_db_fields(capability: CapabilityPayload) -> Dict[str, Any]:
        """
        Maps a CapabilityPayload into a dictionary ready for DB update or create.
        """
        perms = capability.permissions or PermissionFlags()
        
        return {
            "can_view": perms.can_view,
            "can_create": perms.can_create,
            "can_edit": perms.can_edit,
            "can_delete": perms.can_delete,
        }

    @staticmethod
    def extract_metadata(payload_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures all required metadata for logging/tracking is extracted."""
        return {
            "event_id": payload_dict.get("event_id"),
            "provider_id": payload_dict.get("provider_id"),
            "plan_id": payload_dict.get("plan_id"),
            "schema_version": payload_dict.get("schema_version"),
        }
