from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import uuid

class ValidationError(Exception):
    pass

@dataclass
class PermissionFlags:
    can_view: bool = False
    can_create: bool = False
    can_edit: bool = False
    can_delete: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            can_view=bool(data.get("can_view", False)),
            can_create=bool(data.get("can_create", False)),
            can_edit=bool(data.get("can_edit", False)),
            can_delete=bool(data.get("can_delete", False)),
        )

@dataclass
class CapabilityPayload:
    service_id: str
    category_id: Optional[str] = None
    facility_id: Optional[str] = None
    pricing_id: Optional[str] = None
    permissions: PermissionFlags = field(default_factory=PermissionFlags)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            service_id=str(data["service_id"]),
            category_id=data.get("category_id"),
            facility_id=data.get("facility_id"),
            pricing_id=data.get("pricing_id"),
            permissions=PermissionFlags.from_dict(data.get("permissions", {}))
        )

@dataclass
class ServiceTemplatePayload:
    id: str
    name: str
    display_name: str
    icon: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            display_name=str(data["display_name"]),
            icon=str(data.get("icon", "tabler-box"))
        )

@dataclass
class CategoryTemplatePayload:
    id: str
    service_id: str
    name: str
    category_key: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            id=str(data["id"]),
            service_id=str(data["service_id"]),
            name=str(data["name"]),
            category_key=str(data.get("category_key", data.get("name", "")))
        )

@dataclass
class FacilityTemplatePayload:
    id: str
    category_id: Optional[str]
    name: str
    description: str
    protocol_type: str = "MINUTES_BASED"
    duration_minutes: int = 60
    pricing_strategy: str = "FIXED"
    base_price: str = "0.00"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            id=str(data["id"]),
            category_id=str(data["category_id"]) if data.get("category_id") else None,
            name=str(data["name"]),
            description=str(data.get("description", "")),
            protocol_type=str(data.get("protocol_type", "MINUTES_BASED")),
            duration_minutes=int(data.get("duration_minutes", 60)),
            pricing_strategy=str(data.get("pricing_strategy", "FIXED")),
            base_price=str(data.get("base_price", "0.00"))
        )

@dataclass
class PermissionSyncPayload:
    event_id: uuid.UUID
    schema_version: str
    timestamp: str 
    provider_id: uuid.UUID 
    plan_id: str
    capabilities: List[CapabilityPayload]
    templates: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def validate_and_parse(cls, data: Dict[str, Any]):
        try:
            inner_data = data.get("data", {})
            schema_version = str(data.get("schema_version", "1.0"))
            
            # Map legacy 'auth_user_id' -> 'provider_id'
            p_id = inner_data.get("provider_id") or inner_data.get("auth_user_id")
            if not p_id:
                raise ValidationError("Missing provider_id/auth_user_id in payload")

            return cls(
                event_id=uuid.UUID(str(data.get("event_id", uuid.uuid4()))),
                schema_version=schema_version,
                timestamp=str(data.get("timestamp", data.get("occurred_at", timezone.now().isoformat() if 'timezone' in globals() else ""))),
                provider_id=uuid.UUID(str(p_id)),
                plan_id=str(inner_data.get("purchase_id", inner_data.get("plan_id", ""))),
                capabilities=[CapabilityPayload.from_dict(c) for c in inner_data.get("capabilities", inner_data.get("permissions", []))],
                templates=inner_data.get("templates", {})
            )
        except (KeyError, ValueError, TypeError) as e:
            raise ValidationError(f"Invalid PermissionSyncPayload ({str(e)})")
