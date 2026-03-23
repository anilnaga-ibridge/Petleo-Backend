"""
Migration: 0053_add_new_vet_capabilities

PURPOSE:
    Add new Capability DB records for the 3 new veterinary RBAC features:
    - VETERINARY_SCHEDULING  (covers: Schedule, Online Consult, Offline Visits)
    - VETERINARY_METADATA    (covers: Metadata Management page)
    - VETERINARY_CHECKOUT    (covers: Visit Closure, Billing, Invoice)

BACKWARD COMPATIBILITY:
    Any existing ProviderRole that has VETERINARY_VISITS capability will
    automatically receive VETERINARY_SCHEDULING so that Receptionists and
    Doctors who already exist in the DB don't lose access to their schedule view.
"""

from django.db import migrations


def add_new_capabilities(apps, schema_editor):
    Capability = apps.get_model('service_provider', 'Capability')
    ProviderRoleCapability = apps.get_model('service_provider', 'ProviderRoleCapability')

    # 1. Seed the three new Capability records (safe – uses get_or_create)
    new_caps = [
        {
            "key": "VETERINARY_SCHEDULING",
            "label": "Scheduling & Appointments",
            "description": "Access to Schedule, Online Consult and Offline Visits modules.",
            "group": "Scheduling",
        },
        {
            "key": "VETERINARY_METADATA",
            "label": "Metadata Management",
            "description": "Configure pet species, breeds, visit types and other master data.",
            "group": "System Management",
        },
        {
            "key": "VETERINARY_CHECKOUT",
            "label": "Checkout & Billing",
            "description": "Finalize visits, process payments and generate invoices.",
            "group": "Billing",
        },
    ]

    for cap_data in new_caps:
        Capability.objects.get_or_create(
            key=cap_data["key"],
            defaults={
                "label": cap_data["label"],
                "description": cap_data["description"],
                "group": cap_data["group"],
            },
        )

    # 2. Backward-compat: any role that already has VETERINARY_VISITS
    #    should also get VETERINARY_SCHEDULING (receptionist / doctor roles).
    roles_with_visits = ProviderRoleCapability.objects.filter(
        capability_key="VETERINARY_VISITS"
    ).values_list("provider_role_id", flat=True).distinct()

    for role_id in roles_with_visits:
        ProviderRoleCapability.objects.get_or_create(
            provider_role_id=role_id,
            capability_key="VETERINARY_SCHEDULING",
            defaults={
                "can_view": True,
                "can_create": True,
                "can_edit": True,
                "can_delete": False,
            },
        )


def reverse_add_new_capabilities(apps, schema_editor):
    """Remove the new capabilities and their role mappings."""
    Capability = apps.get_model('service_provider', 'Capability')
    ProviderRoleCapability = apps.get_model('service_provider', 'ProviderRoleCapability')

    new_keys = ["VETERINARY_SCHEDULING", "VETERINARY_METADATA", "VETERINARY_CHECKOUT"]
    ProviderRoleCapability.objects.filter(capability_key__in=new_keys).delete()
    Capability.objects.filter(key__in=new_keys).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('service_provider', '0052_providerrolecapability_can_create_and_more'),
    ]

    operations = [
        migrations.RunPython(
            add_new_capabilities,
            reverse_code=reverse_add_new_capabilities,
        ),
    ]
