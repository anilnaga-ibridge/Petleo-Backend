from users.models import EmailTemplate
print(f"Total templates: {EmailTemplate.objects.count()}")
for t in EmailTemplate.objects.all():
    print(f"ID: {t.id}, Name: {t.name}, Role: {t.role}, Type: {t.type}, Default: {t.is_default}, Active: {t.is_active}, Updated: {t.updated_at}")
