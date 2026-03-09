import logging
import requests
import time
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from .models import VisitGroup, Booking, BookingItem, BookingStatusHistory
from .services import SlotLockService, AvailabilityCacheService

logger = logging.getLogger(__name__)

class VisitPlanner:
    """Layer 1: Pure Time & Availability Logic (Deterministic)"""
    @staticmethod
    def plan_visit(organization_id, pet_id, items_data):
        planned_items = []
        last_end_time = None
        
        # Strictly Deterministic: If unavailable at requested time, FAIL early.
        # No auto-search/backtracking as per Tier-1 Clean Architecture manifesto.
        for item in items_data:
            # Resolve service details
            resolve_url = f"http://localhost:8002/api/provider/resolve-details/?service_id={item['service_id']}&facility_id={item['facility_id']}&provider_id={organization_id}"
            resolve_resp = requests.get(resolve_url, timeout=5)
            if resolve_resp.status_code != 200:
                raise ValueError(f"SERVICE_NOT_FOUND: {item['service_id']}")
            
            details = resolve_resp.json()
            duration = details.get('duration_minutes', 60)
            mode = details.get('execution_mode', 'SEQUENTIAL')
            buffer = details.get('buffer_minutes', 0)

            # Determine start time
            start_dt = datetime.fromisoformat(item['preferred_start'].replace('Z', '+00:00'))
            
            if mode == 'SEQUENTIAL' and last_end_time:
                 if start_dt < last_end_time:
                     start_dt = last_end_time + timedelta(minutes=buffer)
            
            end_dt = start_dt + timedelta(minutes=duration)

            # Check Staff Assignment for this specific window
            employee_id = VisitPlanner._find_employee(organization_id, item['facility_id'], start_dt)
            if not employee_id:
                raise ValueError("EMPLOYEE_UNAVAILABLE")

            planned_items.append({
                **item,
                'start_dt': start_dt,
                'end_dt': end_dt,
                'employee_id': employee_id,
                'snapshot': details,
                'price_snapshot': details.get('price_snapshot', {})
            })
            last_end_time = end_dt

        return planned_items

    @staticmethod
    def _find_employee(organization_id, facility_id, start_dt):
        assign_url = f"http://localhost:8002/api/provider/availability/{organization_id}/smart-assignment/"
        assign_params = {
            "date": start_dt.strftime('%Y-%m-%d'),
            "start_time": start_dt.strftime('%H:%M'),
            "facility_id": facility_id
        }
        try:
            resp = requests.get(assign_url, params=assign_params, timeout=5)
            if resp.status_code == 200:
                return resp.json().get('employee_id')
        except Exception:
            pass
        return None

class VisitLocker:
    """Layer 2: Redis Multi-Lock Orchestration (Safe try/finally)"""
    def __init__(self, locks):
        self.locks = locks # List of (emp_id, dt)
        self.locked = False

    def __enter__(self):
        if not self.locks:
            return self
        
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
    def persist_visit(owner, organization_id, pet_id, processed_items, idempotency_key=None):
        # 1. Idempotency Check
        if idempotency_key:
            existing = VisitGroup.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return existing # Return existing instead of error (Standard Idempotency behavior)

        # 2. Final Pet Overlap Check (Truth Layer)
        min_start = min(i['start_dt'] for i in processed_items)
        max_end = max(i['end_dt'] for i in processed_items)
        
        if BookingItem.objects.filter(
            pet_id=pet_id,
            status__in=['PENDING', 'CONFIRMED', 'IN_PROGRESS'],
            selected_time__lt=max_end,
            end_time__gt=min_start
        ).exists():
            raise ValueError("PET_BUSY: Pet has an overlapping appointment.")

        try:
            with transaction.atomic():
                # 3. Create VisitGroup
                visit = VisitGroup.objects.create(
                    organization_id=organization_id,
                    pet_id=pet_id,
                    owner=owner,
                    idempotency_key=idempotency_key,
                    status='PENDING'
                )

                # 4. Create Master Booking
                total_price = sum(float(i['price_snapshot'].get('base_price', 0)) for i in processed_items)
                master_booking = Booking.objects.create(
                    owner=owner,
                    total_price=total_price,
                    status='PENDING'
                )

                # 5. Create Booking Items
                for i in processed_items:
                    BookingItem.objects.create(
                        booking=master_booking,
                        visit_group=visit,
                        provider_id=organization_id,
                        service_id=i['service_id'],
                        facility_id=i['facility_id'],
                        pet_id=pet_id,
                        selected_time=i['start_dt'],
                        end_time=i['end_dt'],
                        assigned_employee_id=i['employee_id'],
                        service_snapshot=i['snapshot'],
                        price_snapshot=i['price_snapshot'],
                        status='PENDING'
                    )

                # 6. Final Concurrency Check (Safety)
                for i in processed_items:
                    # Use select_for_update or count check
                    if BookingItem.objects.filter(
                        assigned_employee_id=i['employee_id'],
                        selected_time=i['start_dt'],
                        status__in=['PENDING', 'CONFIRMED', 'IN_PROGRESS']
                    ).count() > 1:
                        raise ValueError("CONCURRENCY_FAIL: Slot taken during transaction.")

                # 7. Invalidate Caches
                for i in processed_items:
                    transaction.on_commit(lambda emp=i['employee_id'], fac=i['facility_id'], date=i['start_dt'].date(): 
                        AvailabilityCacheService.invalidate_slots(emp, fac, date)
                    )

                return visit
        except Exception as e:
            logger.error(f"Persistence failure: {e}")
            raise e

class VisitCoordinatorService:
    """The High-Level Orchestrator (Orchestra Conductor)"""
    @staticmethod
    def create_visit_cart(owner, items_data, organization_id, idempotency_key=None):
        start_perf = time.perf_counter()
        if not items_data:
            raise ValueError("CART_EMPTY")

        pet_id = items_data[0]['pet_id']

        # Step 1: Planning (Time Logic & Backtracking)
        processed_items = VisitPlanner.plan_visit(organization_id, pet_id, items_data)

        # Step 2: Locking (Multi-Lock with context manager safety)
        # We lock both Employees AND the Pet to prevent concurrent disparate carts for same dog
        locks = []
        # Employee locks
        for i in processed_items:
            locks.append((
                i['employee_id'], 
                i['service_id'], 
                i['facility_id'], 
                i['start_dt'], 
                i['end_dt']
            ))
        
        # Pet lock (Covers the entire span of the visit using 'pet:{id}' as the employee ID slot)
        min_start = min(i['start_dt'] for i in processed_items)
        max_end = max(i['end_dt'] for i in processed_items)
        locks.append((f"pet:{pet_id}", "SYSTEM_SERVICE", "SYSTEM_FACILITY", min_start, max_end))

        with VisitLocker(locks):
            # Step 3: Persistence (Idempotency & DB Transaction)
            visit = VisitPersister.persist_visit(
                owner=owner,
                organization_id=organization_id,
                pet_id=pet_id,
                processed_items=processed_items,
                idempotency_key=idempotency_key
            )

            latency = (time.perf_counter() - start_perf) * 1000
            logger.info(f"[Metrics] Multi-service visit created. Total latency: {latency:.2f}ms. Items: {len(processed_items)}")
            return visit
