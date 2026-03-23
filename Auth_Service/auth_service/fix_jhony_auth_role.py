import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_service.settings')
django.setup()

from users.models import User, UserRole, Role, RolePermission, Permission

JHONY_EMAIL = 'jhony@gmail.com'
# This is the clinic ID from the API request
CLINIC_ID = 'e56f30a2-cd65-45c3-8029-2152ed13904a'

u = User.objects.filter(email=JHONY_EMAIL).first()
if not u:
    print('User not found in Auth Service')
    exit()

print(f'User: {u.email} (id={u.id})')

# 1. Find the "Veterinary Doctor" / "Doctor" role
doctor_role = Role.objects.filter(name__icontains='doctor').first()
if not doctor_role:
    print('Could not find a Doctor role! Available roles:')
    for r in Role.objects.all():
        print(f'  {r.name} (id={r.id})')
    exit()

print(f'Found role: {doctor_role.name} (id={doctor_role.id})')

# 2. Show what permissions this role has
perms = RolePermission.objects.filter(role=doctor_role).select_related('permission')
print(f'Permissions for {doctor_role.name}: {len(perms)}')
for p in perms:
    print(f'  {p.permission.capability_key}: V={p.can_view} C={p.can_create} E={p.can_edit} D={p.can_delete}')

# 3. Assign or update the UserRole
ur, created = UserRole.objects.get_or_create(
    user=u, 
    clinic_id=CLINIC_ID,
    defaults={'role': doctor_role}
)
if not created and ur.role != doctor_role:
    ur.role = doctor_role
    ur.save()
    print(f'\n✅ Updated UserRole to {doctor_role.name} @ clinic {CLINIC_ID}')
elif created:
    print(f'\n✅ Created UserRole: {doctor_role.name} @ clinic {CLINIC_ID}')
else:
    print(f'\n✅ UserRole already exists: {ur.role.name} @ clinic {CLINIC_ID}')
