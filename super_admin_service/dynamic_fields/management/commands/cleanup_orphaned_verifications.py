from django.core.management.base import BaseCommand
from dynamic_fields.models import ProviderDocumentVerification
from admin_core.models import VerifiedUser

class Command(BaseCommand):
    help = 'Cleans up ProviderDocumentVerification records that do not have a corresponding VerifiedUser.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting cleanup of orphaned verification documents...'))

        verifications = ProviderDocumentVerification.objects.all()
        deleted_count = 0
        
        for doc in verifications:
            # Check if User exists
            if not VerifiedUser.objects.filter(auth_user_id=doc.auth_user_id).exists():
                self.stdout.write(self.style.ERROR(f'🗑️ Deleting orphaned document {doc.id} (auth_user_id: {doc.auth_user_id})'))
                doc.delete()
                deleted_count += 1
        
        if deleted_count > 0:
            self.stdout.write(self.style.SUCCESS(f'✅ Successfully deleted {deleted_count} orphaned verification documents.'))
        else:
            self.stdout.write(self.style.SUCCESS('✨ No orphaned documents found. Database is clean.'))
