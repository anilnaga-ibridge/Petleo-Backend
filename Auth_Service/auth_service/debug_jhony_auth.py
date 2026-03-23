import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_service.settings')
django.setup()

from users.models import User, UserRole, Role, RolePermission, Permission

u = User.objects.filter(email='jhony@gmail.com').first()
if not u:
    print('User not found in Auth Service')
else:
    print(f'User: {u.email} (id={u.id})')
    clinic_id = getattr(u, 'clinic_id', None)
    print(f'clinic_id on user: {clinic_id}')
    
    urs = UserRole.objects.filter(user=u).select_related('role')
    print(f'UserRoles assigned: {[(ur.role.name, str(ur.clinic_id)) for ur in urs]}')
    
    for ur in urs:
        perms = RolePermission.objects.filter(role=ur.role).select_related('permission')
        print(f'\n  Role: {ur.role.name} @ clinic {ur.clinic_id}')
        for p in perms:
            print(f'    {p.permission.capability_key}: V={p.can_view} C={p.can_create} E={p.can_edit} D={p.can_delete}')

    # List all available roles
    print('\nAll Roles in Auth Service:')
    for r in Role.objects.all():
        print(f'  [{r.id}] {r.name}')
