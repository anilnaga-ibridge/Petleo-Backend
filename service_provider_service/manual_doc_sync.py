import os
import django
import json

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import ProviderDocument
from service_provider.kafka_producer import publish_document_uploaded

def sync_documents():
    docs = ProviderDocument.objects.all()
    print(f"🔍 Found {docs.count()} documents to sync.")
    
    # We need a mock request to build absolute URIs or we hardcode it if needed.
    # Actually, document.file.url usually gives the relative path. 
    # Let's assume the base URL for now if we can't get it from settings.
    base_url = "http://127.0.0.1:8002"
    
    success_count = 0
    for doc in docs:
        try:
            file_url = f"{base_url}{doc.file.url}" if doc.file and not doc.file.url.startswith("http") else getattr(doc.file, 'url', '')
            
            print(f"📤 Syncing: {doc.filename} for User: {doc.verified_user.auth_user_id}")
            
            publish_document_uploaded(
                provider_id=doc.verified_user.auth_user_id,
                document_id=doc.id,
                definition_id=doc.definition_id,
                file_url=file_url,
                filename=doc.filename
            )
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to sync document {doc.id}: {e}")

    print(f"✅ Finished! Successfully synced {success_count}/{docs.count()} documents.")

if __name__ == "__main__":
    sync_documents()
