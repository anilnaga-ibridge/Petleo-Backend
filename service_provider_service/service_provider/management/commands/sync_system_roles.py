from django.core.management.base import BaseCommand
from service_provider.models import ServiceProvider, ProviderRole
from service_provider.role_templates import get_role_templates
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Syncs system role templates from role_templates.py to the database for all providers."

    def handle(self, *args, **options):
        self.stdout.write("🔄 Starting System Role Synchronization...")
        
        # 1. Load latest templates from code
        all_data = get_role_templates()
        templates = all_data.get('templates', [])
        
        # 2. Iterate through all ServiceProviders
        providers = ServiceProvider.objects.all()
        total_synced = 0
        
        for provider in providers:
            for template in templates:
                # Find or Create the System Role for this provider
                role, created = ProviderRole.objects.get_or_create(
                    provider=provider,
                    name=template.get('name'),
                    defaults={
                        'description': template.get('description'),
                        'is_system_role': True,
                        'is_active': True,
                        'version': 1
                    }
                )
                
                # 🛠 Update existing role if template changed
                if not created:
                    needs_update = False
                    if role.description != template.get('description'):
                        role.description = template.get('description')
                        needs_update = True
                    
                    if not role.is_system_role:
                        role.is_system_role = True
                        needs_update = True
                        
                    if needs_update:
                        # 🦾 Bump Version to invalidate staff caches automatically
                        role.version += 1
                        role.save()
                        total_synced += 1
                        self.stdout.write(f"   ✅ Updated '{role.name}' for {provider.email} (v{role.version})")
                else:
                    self.stdout.write(f"   ✨ Created '{role.name}' for {provider.email}")
                    total_synced += 1

        self.stdout.write(self.style.SUCCESS(f"🏁 Successfully synced {total_synced} system roles across all providers."))
