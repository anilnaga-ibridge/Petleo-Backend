from plans_coupens.models import Plan, PlanCapability

plan = Plan.objects.filter(title__icontains='Basic').first()
if plan:
    print(f'Plan: {plan.title}')
    caps = PlanCapability.objects.filter(plan=plan)
    print(f'Total Capabilities: {caps.count()}')
    for pc in caps:
        svc = pc.service.display_name if pc.service else 'NoService'
        cat = pc.category.name if pc.category else 'NoCategory'
        print(f'- Service: {svc}, Category: {cat}, Permissions: {pc.permissions}')
else:
    print('Plan not found')
