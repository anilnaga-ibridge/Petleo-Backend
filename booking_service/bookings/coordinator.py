import logging
import requests
import time
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from .models import VisitGroup, Booking, BookingItem, BookingStatusHistory
from .services import SlotLockService, AvailabilityCacheService

logger = logging.getLogger(__name__)

from .engines.router import BookingRouter
from rest_framework.exceptions import ValidationError

class VisitPlanner:
    """Layer 1: Pure Time & Availability Logic (Deterministic)"""
    @staticmethod
    def plan_visit(organization_id, pet_id, items_data):
        planned_items = []
        last_end_time = None
        
        for item in items_data:
            # 1. Resolve service details and pricing rules
            resolve_url = f"http://localhost:8002/api/provider/resolve-details/?service_id={item['service_id']}&facility_id={item['facility_id']}&provider_id={organization_id}"
            resolve_resp = requests.get(resolve_url, timeout=5)
            if resolve_resp.status_code != 200:
                raise ValueError(f"SERVICE_NOT_FOUND: {item['service_id']}")
            
            details = resolve_resp.json()
            pricing_rule = details.get('price_snapshot', {})
            duration = details.get('duration_minutes', 60)
            mode = details.get('execution_mode', 'SEQUENTIAL')
            buffer = details.get('buffer_minutes', 0)

            # 2. Determine start and end times
            start_dt = datetime.fromisoformat(item['preferred_start'].replace('Z', '+00:00'))
            if mode == 'SEQUENTIAL' and last_end_time:
                 if start_dt < last_end_time:
                     start_dt = last_end_time + timedelta(minutes=buffer)
            
            end_dt = start_dt + timedelta(minutes=duration)

            # 3. Instantiate Engine for specific logic and pricing
            engine = BookingRouter.get_engine(pricing_rule)
            
            # Validation context for engine
            engine_context = {
                "selected_time": start_dt,
                "end_time": end_dt,
                "provider_id": organization_id,
                "facility_id": item['facility_id']
            }
            engine.validate_availability(engine_context)
            total_price = engine.calculate_price(engine_context)

            # 4. Check Staff Assignment
            employee_data = VisitPlanner._fetch_employee_assignment(organization_id, item['facility_id'], start_dt)
            if not employee_data:
                raise ValueError("EMPLOYEE_UNAVAILABLE")

            planned_items.append({
                **item,
                'start_dt': start_dt,
                'end_dt': end_dt,
                'total_price': total_price,
                'employee_id': employee_data['id'],
                'employee_snapshot': employee_data.get('snapshot', {}),
                'resource_id': item['facility_id'],
                'service_snapshot': details,
                'price_snapshot': pricing_rule,
                'engine_snapshot': engine.get_context_snapshot(),
                'pet_snapshot': item.get('pet_snapshot', {}),
                'owner_snapshot': item.get('owner_snapshot', {})
            })
            last_end_time = end_dt

        return planned_items

    @staticmethod
    def _fetch_employee_assignment(organization_id, facility_id, start_dt):
        assign_url = f"http://localhost:8002/api/provider/availability/{organization_id}/smart-assignment/"
        params = {
            "date": start_dt.strftime('%Y-%m-%d'),
            "start_time": start_dt.strftime('%H:%M'),
            "facility_id": facility_id
        }
        try:
            resp = requests.get(assign_url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'id': data.get('employee_id'),
                    'snapshot': data.get('employee_snapshot', {})
                }
        except Exception:
            pass
        return None

class VisitLocker:
    """Layer 2: Redis Multi-Lock Orchestration"""
    def __init__(self, locks):
        # locks should be a list of (identifier, dt)
        self.locks = locks
        self.locked = False

    def __enter__(self):
        if not self.locks:
            return self
        
        # SlotLockService.lock_multiple handles the locking in order of the list
        self.locked = SlotLockService.lock_multiple(self.locks)
        if not self.locked:
            raise ValueError("LOCK_CONFLICT: One or more slots were just taken.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.locked:
            SlotLockService.release_multiple(self.locks)
            self.locked = False

class VisitPersister:
    """Layer 3: DB Transaction & Idempotency"""
    @staticmethod
    def persist_visit(owner_id, organization_id, pet_id, processed_items, idempotency_key=None, owner_snapshot=None):
        if idempotency_key:
            existing = VisitGroup.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return existing

        # Final Pet Overlap Check
        min_start = min(i['start_dt'] for i in processed_items)
        max_end = max(i['end_dt'] for i in processed_items)
        
        if BookingItem.objects.filter(
            pet_id=pet_id,
            status__in=['PENDING', 'CONFIRMED', 'IN_PROGRESS'],
            selected_time__lt=max_end,
            end_time__gt=min_start
        ).exists():
            raise ValueError("PET_BUSY")

        try:
            with transaction.atomic():
                visit = VisitGroup.objects.create(
                    organization_id=organization_id,
                    pet_id=pet_id,
                    owner_id=owner_id,
                    idempotency_key=idempotency_key,
                    status='PENDING'
                )

                total_price = sum(float(i['total_price']) for i in processed_items)
                master_booking = Booking.objects.create(
                    owner_id=owner_id,
                    owner_snapshot=owner_snapshot,
                    total_price=total_price,
                    status='PENDING'
                )

                for i in processed_items:
                    BookingItem.objects.create(
                        booking=master_booking,
                        visit_group=visit,
                        provider_id=organization_id,
                        service_id=i['service_id'],
                        facility_id=i['facility_id'],
                        pet_id=pet_id,
                        owner_id=owner_id,
                        selected_time=i['start_dt'],
                        end_time=i['end_dt'],
                        assigned_employee_id=i['employee_id'],
                        resource_id=i['resource_id'],
                        pet_snapshot=i['pet_snapshot'],
                        owner_snapshot=owner_snapshot or i['owner_snapshot'],
                        employee_snapshot=i['employee_snapshot'],
                        service_snapshot=i['service_snapshot'],
                        price_snapshot=i['price_snapshot'],
                        status='PENDING'
                    )

                # Final Concurrency Check
                for i in processed_items:
                    if BookingItem.objects.filter(
                        assigned_employee_id=i['employee_id'],
                        selected_time=i['start_dt'],
                        status__in=['PENDING', 'CONFIRMED', 'IN_PROGRESS']
                    ).count() > 1:
                        raise ValueError("CONCURRENCY_FAIL")

                for i in processed_items:
                    transaction.on_commit(lambda emp=i['employee_id'], fac=i['facility_id'], date=i['start_dt'].date(): 
                        AvailabilityCacheService.invalidate_slots(emp, fac, date)
                    )

                return visit
        except Exception as e:
            logger.error(f"Persistence failure: {e}")
            raise e

class VisitCoordinatorService:
    """High-Level Orchestrator"""
    @staticmethod
    def create_visit_cart(owner_id, items_data, organization_id, idempotency_key=None, owner_snapshot=None):
        start_perf = time.perf_counter()
        if not items_data:
            raise ValueError("CART_EMPTY")

        pet_id = items_data[0]['pet_id']

        # 1. Planning
        processed_items = VisitPlanner.plan_visit(organization_id, pet_id, items_data)

        # 2. Locking Sequence (STRICT ORDER: Pet -> Employee -> Resource)
        locks = []
        
        # 1. Pet Lock
        min_start = min(i['start_dt'] for i in processed_items)
        locks.append((f"pet:{pet_id}", min_start))
        
        # 2. Employee Locks
        # Sort employees to avoid deadlocks if multiple employees are involved
        unique_emps = sorted(list(set(i['employee_id'] for i in processed_items)))
        for emp_id in unique_emps:
            # For simplicity, we lock the start time of the first item for this employee in the cart
            emp_start = min(i['start_dt'] for i in processed_items if i['employee_id'] == emp_id)
            locks.append((f"emp:{emp_id}", emp_start))
        
        # 3. Resource Locks
        unique_res = sorted(list(set(i['resource_id'] for i in processed_items)))
        for res_id in unique_res:
            res_start = min(i['start_dt'] for i in processed_items if i['resource_id'] == res_id)
            locks.append((f"res:{res_id}", res_start))

        with VisitLocker(locks):
            # 3. Persistence
            visit = VisitPersister.persist_visit(
                owner_id=owner_id,
                organization_id=organization_id,
                pet_id=pet_id,
                processed_items=processed_items,
                idempotency_key=idempotency_key,
                owner_snapshot=owner_snapshot
            )

            latency = (time.perf_counter() - start_perf) * 1000
            logger.info(f"[Metrics] Visit {visit.id} created. Latency: {latency:.2f}ms")
            return visit
