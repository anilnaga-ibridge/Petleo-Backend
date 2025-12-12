from users.models import EmailTemplate
count = EmailTemplate.objects.filter(name="Welcome Email Copy").update(type='automatic')
print(f"Updated {count} templates to automatic")
