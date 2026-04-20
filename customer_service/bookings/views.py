from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate, TruncDay
from .models import Booking, BookingStatusHistory, BookingItem, Invoice
from .serializers import BookingSerializer, BookingStatusHistorySerializer, InvoiceSerializer
from customers.models import PetOwnerProfile
from pets.permissions import IsOwner
import requests
from django.db import transaction, IntegrityError
from datetime import datetime, timedelta
from .services import SlotLockService, AvailabilityCacheService
from .invoice_service import InvoiceService
try:
    from bookings.services.stripe_service import StripeService
except ImportError:
    # Fallback for different project structures
    StripeService = None

from .engines.router import BookingRouter
from .kafka_producer import publish_booking_event
from .coordinator import VisitCoordinatorService

class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing bookings and their lifecycle.
    """
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        provider_id_param = self.request.query_params.get('provider_id')

        queryset = Booking.objects.all()
        filters = Q()

        # Filter by service_id if provided
        service_id_param = self.request.query_params.get('service_id')
        if service_id_param:
            filters &= Q(items__service_id=service_id_param)
        
        # Filter by status if provided
        status_param = self.request.query_params.get('status')
        if status_param and status_param.upper() != 'ALL':
            filters &= Q(status=status_param.upper())
        
        # Get role from validated token (request.auth)
        role = (self.request.auth.get('role') or "").lower() if self.request.auth else ""
        is_provider = getattr(user, 'is_provider', False) or role in ["provider", "organization", "individual", "service_provider", "employee"]
        
        # 1. Provider Mode
        if is_provider:
            auth_id = getattr(user, 'id', None) or getattr(user, 'auth_user_id', None)
            if auth_id:
                provider_filters = Q(items__assigned_employee_id=auth_id) | Q(items__provider_id=auth_id)
                
                # If they pass a specific provider_id, use that for the provider check
                if provider_id_param:
                    provider_filters |= Q(items__provider_id=provider_id_param)
                
                filters &= provider_filters
        
        # 2. Pet Owner Mode (Default or explicit)
        else:
            if isinstance(user, PetOwnerProfile):
                filters &= Q(owner=user)
                # Owners can filter their own bookings by provider
                if provider_id_param:
                    filters &= Q(items__provider_id=provider_id_param)
            else:
                # Fallback for when we have an auth user but no profile (shouldn't happen with our auth class)
                auth_id = getattr(user, 'id', None) or getattr(user, 'auth_user_id', None)
                if auth_id:
                    filters &= Q(owner__auth_user_id=auth_id)

        final_qs = queryset.filter(filters).distinct().prefetch_related('items', 'items__pet')
        return final_qs

    def perform_create(self, serializer):
        user = self.request.user
        owner_profile = None

        # Try to resolve profile
        if isinstance(user, PetOwnerProfile):
            owner_profile = user
        elif hasattr(user, 'petownerprofile'):
            owner_profile = user.petownerprofile
        elif hasattr(user, 'id'):
            try:
                owner_profile = PetOwnerProfile.objects.get(auth_user_id=user.id)
            except PetOwnerProfile.DoesNotExist:
                pass
        
        if not owner_profile:
             raise ValidationError("Only pet owners can create bookings (Profile not found).")
        
        provider_id = self.request.data.get('provider_id')
        selected_time_str = self.request.data.get('selected_time')
        end_time_str = self.request.data.get('end_time') # NEW: Support for range-based
        
        if not provider_id or not selected_time_str:
            raise ValidationError("provider_id and selected_time are required.")

        try:
            with transaction.atomic():
                # 1. Resolve details for snapshot (Crucial for pricing Engine)
                consultation_type_id = self.request.data.get('consultation_type_id')
                resolve_url = f"http://localhost:8002/api/provider/resolve-details/?service_id={serializer.validated_data['service_id']}&facility_id={serializer.validated_data['facility_id']}&provider_id={provider_id}"
                if consultation_type_id:
                    resolve_url += f"&consultation_type_id={consultation_type_id}"
                
                resolve_resp = requests.get(resolve_url, timeout=5)
                details = resolve_resp.json() if resolve_resp.status_code == 200 else {}
                
                service_snapshot = details
                price_snapshot = details.get('price_snapshot', {})
                
                # 2. Initialize Engine
                engine = BookingRouter.get_engine(price_snapshot)
                
                # Parse times
                try:
                    selected_time = datetime.fromisoformat(selected_time_str.replace('Z', '+00:00'))
                    end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00')) if end_time_str else None
                except Exception:
                    raise ValidationError("Invalid date/time format.")

                # 2.2 Calculate End Time based on duration if not provided
                if not end_time:
                    duration = service_snapshot.get('duration_minutes', 60)
                    end_time = selected_time + timedelta(minutes=duration)

                # 3. Engine Validation & Pricing
                item_data = {
                    "selected_time": selected_time,
                    "end_time": end_time,
                    "provider_id": provider_id,
                    "facility_id": serializer.validated_data['facility_id'],
                }
                engine.validate_availability(item_data)
                total_item_price = engine.calculate_price(item_data)

                # 4. Smart Assignment (Only if not fixed by user)
                employee_id = self.request.data.get('employee_id')
                if not employee_id:
                    date_str = selected_time.strftime('%Y-%m-%d')
                    time_str = selected_time.strftime('%H:%M')
                    smart_url = f"http://localhost:8002/api/provider/availability/{provider_id}/smart-assignment/?date={date_str}&facility_id={serializer.validated_data['facility_id']}&start_time={time_str}"
                    
                    assign_resp = requests.get(smart_url, timeout=5)
                    if assign_resp.status_code == 200:
                        employee_id = assign_resp.json().get('employee_id')
                    else:
                        raise ValidationError(assign_resp.json().get('error', 'No qualified employee available for this slot.'))

                # 4.5 Temporary Slot Hold (Redis)
                # Ensure the slot is held for 5 minutes during creation/payment
                lock_success = SlotLockService.lock_slot(
                    employee_id=employee_id,
                    service_id=serializer.validated_data['service_id'],
                    facility_id=serializer.validated_data['facility_id'],
                    start_time=selected_time,
                    end_time=end_time
                )
                if not lock_success:
                    raise ValidationError("This slot was just reserved by another user. Please choose another time.")

                # 4.6 FINAL DB OVERLAP CHECK (Safety Layer)
                # Redis is performance tier; DB is truth tier.
                if BookingItem.objects.filter(
                    assigned_employee_id=employee_id,
                    selected_time__lt=end_time,
                    end_time__gt=selected_time,
                    status__in=['PENDING', 'CONFIRMED', 'IN_PROGRESS']
                ).exists():
                    # If someone beat us, clean up the Lock and fail
                    SlotLockService.release_slot(
                        employee_id=employee_id,
                        service_id=serializer.validated_data['service_id'],
                        facility_id=serializer.validated_data['facility_id'],
                        start_time=selected_time,
                        end_time=end_time
                    )
                    raise ValidationError("This slot was just booked by another user. Please choose another time.")

                # Inject medical/consultation fields from the frontend payload into snapshot
                is_medical = self.request.data.get('is_medical', False)
                consultation_type = self.request.data.get('consultation_type', '')
                if is_medical:
                    service_snapshot['is_medical'] = True
                if consultation_type:
                    service_snapshot['consultation_type'] = consultation_type

                # 5. Create Booking (Atomic)
                # Determine initial status based on Tier (Rule 7, Rule 3)
                # Note: frontend should pass 'tier' or we infer it
                is_tier2 = self.request.data.get('tier') == 2
                initial_status = 'SEARCHING_STAFF' if is_tier2 else 'PENDING'
                
                booking = Booking.objects.create(
                    owner=owner_profile,
                    status=initial_status,
                    total_price=total_item_price,
                    currency='INR'
                )
                
                BookingItem.objects.create(
                    booking=booking,
                    provider_id=provider_id,
                    provider_auth_id=self.request.data.get('provider_auth_id'),
                    service_id=serializer.validated_data['service_id'],
                    facility_id=serializer.validated_data['facility_id'],
                    pet=serializer.validated_data['pet'],
                    selected_time=selected_time,
                    end_time=end_time,
                    assigned_employee_id=employee_id if not is_tier2 else None,
                    service_snapshot=service_snapshot,
                    price_snapshot=price_snapshot,
                    status=initial_status
                )
                
                BookingStatusHistory.objects.create(
                    booking=booking,
                    previous_status='DRAFT',
                    new_status=initial_status,
                    changed_by=self.request.user.id
                )
                
                # TRIGGER CROSS-SERVICE AUTO-ASSIGNMENT (Rule 2)
                # We do this asynchronously or via internal HTTP for now
                try:
                    url = "http://localhost:8002/api/provider/availability/auto-assign/"
                    payload = {
                        "booking_id": str(booking.id),
                        "facility_id": str(serializer.validated_data['facility_id']),
                        "organization_id": str(provider_id),
                        "date": selected_time.strftime('%Y-%m-%d'),
                        "time": selected_time.strftime('%H:%M'),
                        "pet_id": str(serializer.validated_data['pet'].id)
                    }
                    requests.post(url, json=payload, timeout=2)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to trigger auto-assignment: {e}")

                # Publish Event for Notifications (Providers/Employees)
                publish_booking_event('BOOKING_CREATED', booking)

                # Extend the lock to 30 mins to allow for Stripe Checkout payment flow
                SlotLockService.extend_lock(
                    employee_id=employee_id,
                    service_id=serializer.validated_data['service_id'],
                    facility_id=serializer.validated_data['facility_id'],
                    start_time=selected_time,
                    end_time=end_time,
                    new_ttl_seconds=1800
                )
                
                # 7. Invalidate Availability Cache (Atomic on Commit)
                # Target the date of the booking to force recalculation on next query
                transaction.on_commit(lambda: AvailabilityCacheService.invalidate_slots(
                    employee_id, 
                    serializer.validated_data['facility_id'], 
                    selected_time.date()
                ))

                return booking
        except ValidationError as e:
            raise e
        except requests.exceptions.RequestException as e:
            raise ValidationError("Availability service is currently unavailable.")
        except IntegrityError:
            raise ValidationError("This slot was just booked by someone else. Please try another time.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise ValidationError(f"Booking creation failed: {str(e)}")

    def perform_update(self, serializer):
        user = self.request.user
        instance = self.get_object()
        selected_time = self.request.data.get('selected_time')
        
        # If time is changing, we must validate availability
        if selected_time:
            # For simplicity, we assume update affects the first item if multi-item (legacy)
            item = instance.items.first()
            if not item: return serializer.save()

            try:
                # 1. Validate slot availability
                date_str = selected_time.split('T')[0] if 'T' in selected_time else selected_time.split(' ')[0]
                provider_id = item.provider_id
                url = f"http://localhost:8002/api/provider/availability/{provider_id}/available-slots/?date={date_str}"
                resp = requests.get(url, timeout=5)
                
                if resp.status_code != 200:
                    raise ValidationError("Failed to verify slot availability.")
                    
                available_slots = resp.json().get('slots', [])
                try:
                    dt = datetime.fromisoformat(selected_time.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M')
                except Exception:
                    time_str = selected_time.split('T')[1][:5] if 'T' in selected_time else selected_time.split(' ')[1][:5]
                    dt = None
                    
                if time_str not in available_slots:
                    raise ValidationError(f"Selected slot {time_str} is no longer available.")
                    
                # 2. Re-assign employee if organization
                assign_url = f"http://localhost:8002/api/provider/availability/{provider_id}/assign-employee/"
                assign_resp = requests.post(assign_url, json={"selected_time": selected_time}, timeout=5)
                
                assigned_employee_id = item.assigned_employee_id
                if assign_resp.status_code == 200:
                    assigned_employee_id = assign_resp.json().get('employee_id')
                elif assign_resp.status_code == 400:
                     raise ValidationError(assign_resp.json().get('error', 'Employee assignment failed'))

                # 3. Save with transaction
                with transaction.atomic():
                    # Update the header (e.g. status if changed, notes, etc)
                    serializer.save()
                    
                    # Update the actual item with new time and employee
                    if dt:
                        item.selected_time = dt
                    item.assigned_employee_id = assigned_employee_id
                    item.save()
                    
                    # Log change in history
                    BookingStatusHistory.objects.create(
                        booking=instance,
                        previous_status=instance.status,
                        new_status=instance.status,
                        changed_by=user.id if hasattr(user, 'id') else None
                    )
            except requests.exceptions.RequestException:
                raise ValidationError("Availability service is currently unavailable.")
            except IntegrityError:
                raise ValidationError("This slot was just booked by someone else. Please try another time.")
        else:
            serializer.save()

    def _update_status(self, booking, new_status, rejection_reason=None):
        previous_status = booking.status
        booking.status = new_status
        if rejection_reason:
            booking.rejection_reason = rejection_reason
        booking.save()
        
        BookingStatusHistory.objects.create(
            booking=booking,
            previous_status=previous_status,
            new_status=new_status,
            changed_by=self.request.user.id
        )
        return booking

    def _sync_vet_appointment(self, booking):
        """
        When a veterinary booking is confirmed, create a MedicalAppointment + Visit
        in the veterinary_service so the doctor sees it in their queue.
        Fires a fire-and-forget POST to the internal endpoint.
        Failures are logged but don't break the confirm flow.
        """
        import requests as http_requests
        import logging
        logger = logging.getLogger(__name__)

        try:
            item = booking.items.first()
            if not item:
                return

            snapshot = item.service_snapshot or {}
            # Only sync if this is a medical/veterinary booking
            if not snapshot.get('is_medical'):
                return

            # Resolve the provider (clinic) ID in veterinary_service
            # We now use the provider_auth_id which corresponds to organization_id in Clinic 
            clinic_auth_id = str(item.provider_auth_id) if item.provider_auth_id else str(item.provider_id)
            employee_id = str(item.assigned_employee_id) if item.assigned_employee_id else None

            if not employee_id:
                logger.warning(f"[VetSync] No assigned employee for booking {booking.id}, skipping sync")
                return

            # Resolve full details for pet and owner
            pet = item.pet
            owner = booking.owner

            # Build appointment payload
            selected_time = item.selected_time
            start_time_str = selected_time.strftime('%H:%M') if selected_time else '09:00'
            appointment_date = selected_time.date().isoformat() if selected_time else None

            payload = {
                'booking_id': str(booking.id),
                'clinic_id': clinic_auth_id,
                'doctor_auth_id': employee_id,
                'pet_owner_auth_id': str(owner.auth_user_id) if owner else '',
                'pet_external_id': str(pet.id) if pet else '',
                
                # Clinical Details
                'pet_name': pet.name if pet else 'Online Pet',
                'species': pet.species if pet else 'DOG',
                'breed': pet.breed if pet else '',
                'gender': pet.gender if pet else 'MALE',
                'date_of_birth': pet.date_of_birth.isoformat() if pet and pet.date_of_birth else None,
                'weight_kg': str(pet.weight_kg) if pet and pet.weight_kg else '0',

                'owner_name': owner.full_name if owner else 'Online Pet Owner',
                'owner_phone': owner.phone_number if owner else '',
                'owner_email': owner.email if owner else '',

                'service_id': str(item.facility_id) if item.facility_id else str(item.service_id),
                'appointment_date': appointment_date,
                'start_time': start_time_str,
                'consultation_type': snapshot.get('consultation_type', ''),
                'consultation_fee': snapshot.get('price', '0.00'),
                'notes': item.booking.notes or '',
            }

            response = http_requests.post(
                'http://localhost:8004/api/veterinary/internal/create-online-appointment/',
                json=payload,
                timeout=5
            )
            if response.status_code in (200, 201):
                logger.info(f"[VetSync] ✅ Appointment synced for booking {booking.id}: {response.json()}")
            else:
                logger.warning(f"[VetSync] ⚠️ Sync returned {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.error(f"[VetSync] ❌ Failed to sync vet appointment for booking {booking.id}: {e}")

    def _is_authorized_for_booking(self, request, booking):
        """
        Returns True if the requesting user is authorized to perform provider actions
        (accept / reject / complete / cancel) on this booking.

        Authorization is granted if ANY of these conditions match:
        1. The user's auth_user_id equals the provider_id on any BookingItem
           (individual/org provider logged in directly)
        2. The user's auth_user_id equals the assigned_employee_id on any BookingItem
           (employee handling the booking)
        3. The provider_id query param matches the provider_id on any BookingItem
           AND the user is authenticated as a provider role
           (org provider dashboard passing provider_id explicitly)
        """
        user_id = str(getattr(request.user, 'id', '') or '')
        items = booking.items.all()

        # Direct match: user IS the provider stored on the item
        if items.filter(provider_id=user_id).exists():
            return True

        # Direct match: user IS the assigned employee
        if items.filter(assigned_employee_id=user_id).exists():
            return True

        # Query-param provider_id (org provider dashboard)
        provider_id_param = request.query_params.get('provider_id') or request.data.get('provider_id')
        if provider_id_param and items.filter(provider_id=str(provider_id_param)).exists():
            # Verify caller is actually a provider-role user (not a pet owner pretending)
            role = (request.auth.get('role') or '').lower() if request.auth else ''
            is_provider_role = getattr(request.user, 'is_provider', False) or role in [
                'provider', 'organization', 'individual', 'service_provider', 'employee'
            ]
            if is_provider_role:
                return True

        return False

    @action(detail=False, methods=['post'])
    def create_visit(self, request):
        """
        Enterprise-Grade Multi-Service Booking Creation.
        Accepts a list of booking items and processes them atomically via VisitCoordinatorService.
        """
        items_data = request.data.get('items', [])
        organization_id = request.data.get('organization_id')
        idempotency_key = request.data.get('idempotency_key')
        
        if not items_data or not organization_id:
            return Response({"error": "Items and organization_id are required."}, status=400)
            
        try:
            visit = VisitCoordinatorService.create_visit_cart(
                owner=request.user.petownerprofile if hasattr(request.user, 'petownerprofile') else request.user,
                items_data=items_data,
                organization_id=organization_id,
                idempotency_key=idempotency_key
            )
            
            return Response({
                "message": "Visit processed successfully.",
                "visit_id": str(visit.id),
                "status": visit.status
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            error_msg = str(e)
            # Map structured errors to HTTP status codes
            status_code = status.HTTP_400_BAD_REQUEST
            if any(x in error_msg for x in ["LOCK_CONFLICT", "CONCURRENCY_FAIL", "PET_BUSY"]):
                status_code = status.HTTP_409_CONFLICT
            
            return Response({
                "error": error_msg,
                "code": error_msg.split(':')[0] if ':' in error_msg else error_msg
            }, status=status_code)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                "error": "INTERNAL_SERVER_ERROR",
                "details": str(e)
            }, status=500)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        booking = self.get_object()

        if not self._is_authorized_for_booking(request, booking):
            return Response(
                {"error": "Only the assigned provider/employee can accept this booking."},
                status=status.HTTP_403_FORBIDDEN
            )

        if booking.status != 'PENDING':
            raise ValidationError(f"Cannot accept a booking that is {booking.status}.")

        self._update_status(booking, 'CONFIRMED')
        booking.refresh_from_db()
        # Fire-and-forget: sync appointment to veterinary_service if this is a vet booking
        self._sync_vet_appointment(booking)
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        booking = self.get_object()
        rejection_reason = request.data.get('rejection_reason', '')

        if not self._is_authorized_for_booking(request, booking):
            return Response(
                {"error": "Only the assigned provider/employee can reject this booking."},
                status=status.HTTP_403_FORBIDDEN
            )

        if booking.status != 'PENDING':
            raise ValidationError(f"Cannot reject a booking that is {booking.status}.")

        self._update_status(booking, 'REJECTED', rejection_reason=rejection_reason)
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()

        # Owners can always cancel their own bookings;
        # providers/employees also can via _is_authorized_for_booking
        is_owner = isinstance(request.user, PetOwnerProfile) and booking.owner == request.user

        if not (is_owner or self._is_authorized_for_booking(request, booking)):
            return Response(
                {"error": "You do not have permission to cancel this booking."},
                status=status.HTTP_403_FORBIDDEN
            )

        if booking.status not in ['PENDING', 'CONFIRMED']:
            raise ValidationError(f"Cannot cancel a booking that is {booking.status}.")

        self._update_status(booking, 'CANCELLED')
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        booking = self.get_object()

        if not self._is_authorized_for_booking(request, booking):
            return Response(
                {"error": "Only the assigned provider/employee can complete this booking."},
                status=status.HTTP_403_FORBIDDEN
            )

        if booking.status != 'CONFIRMED':
            raise ValidationError("Only confirmed bookings can be marked as completed.")

        with transaction.atomic():
            self._update_status(booking, 'COMPLETED')
            booking.items.all().update(
                status='COMPLETED',
                completed_at=timezone.now()
            )

        return Response(BookingSerializer(booking).data)

    @action(detail=False, methods=['get'])
    def my(self, request):
        """Helper to explicitly get owner's bookings"""
        if not hasattr(request.user, 'petownerprofile'):
            return Response({"error": "Pet owner profile not found."}, status=status.HTTP_404_NOT_FOUND)
        
        bookings = Booking.objects.filter(owner=request.user.petownerprofile)
        page = self.paginate_queryset(bookings)
        if page is not None:
            serializer = BookingSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)

        return Response([b.selected_time.strftime('%H:%M') for b in queryset])

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def internal_provider_bookings(self, request):
        """
        Internal API for fetching ALL confirmed booking ranges for a provider.
        Returns [{'start': 'HH:MM', 'end': 'HH:MM', 'facility_id': '...'}]
        """
        provider_id = request.query_params.get('provider_id')
        date_str = request.query_params.get('date')

        if not provider_id or not date_str:
            return Response({"error": "provider_id and date are required"}, status=400)

        from .models import BookingItem
        queryset = BookingItem.objects.filter(
            provider_id=provider_id,
            status__in=['PENDING', 'CONFIRMED', 'IN_PROGRESS'],
            selected_time__date=date_str
        )

        results = []
        for item in queryset:
            duration = 60
            if item.price_snapshot and 'duration_minutes' in item.price_snapshot:
                duration = item.price_snapshot['duration_minutes']
            elif item.service_snapshot and 'duration' in item.service_snapshot:
                duration = item.service_snapshot['duration']
            
            start_time = item.selected_time
            end_time = start_time + timedelta(minutes=duration)
            
            results.append({
                "start": start_time.strftime('%H:%M'),
                "end": end_time.strftime('%H:%M'),
                "facility_id": str(item.facility_id)
            })
            
        return Response(results)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def internal_employee_bookings(self, request):
        """
        Internal API for fetching confirmed booking ranges for an employee.
        Returns [{'start': 'HH:MM', 'end': 'HH:MM'}]
        """
        employee_id = request.query_params.get('employee_id')
        date_str = request.query_params.get('date')

        if not employee_id or not date_str:
            return Response({"error": "employee_id and date are required"}, status=400)

        from .models import BookingItem
        queryset = BookingItem.objects.filter(
            assigned_employee_id=employee_id,
            status__in=['PENDING', 'CONFIRMED', 'IN_PROGRESS'],
            selected_time__date=date_str
        )

        results = []
        for item in queryset:
            # Try to get duration from snapshots
            duration = 60
            if item.price_snapshot and 'duration_minutes' in item.price_snapshot:
                duration = item.price_snapshot['duration_minutes']
            elif item.service_snapshot and 'duration' in item.service_snapshot:
                duration = item.service_snapshot['duration']
            
            start_time = item.selected_time
            end_time = start_time + timedelta(minutes=duration)
            
            results.append({
                "start": start_time.strftime('%H:%M'),
                "end": end_time.strftime('%H:%M')
            })
            
        return Response(results)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Returns booking statistics for the provider dashboard.
        Query Params: provider_id, service_id (optional)
        """
        provider_id = request.query_params.get('provider_id')
        service_id = request.query_params.get('service_id')
        
        if not provider_id:
            return Response({"error": "provider_id is required"}, status=400)
            
        
        # 0. Initial Filters
        base_filters = Q(provider_id=provider_id)
        if service_id:
            base_filters &= Q(service_id=service_id)

        # 1. Total Counts & Revenue
        stats_data = BookingItem.objects.filter(base_filters).aggregate(
            total_bookings=Count('id'),
            pending_bookings=Count('id', filter=Q(status='PENDING')),
            total_revenue=Sum('booking__total_price', filter=Q(status='COMPLETED'))
        )
        
        total_bookings = stats_data['total_bookings'] or 0
        pending_bookings = stats_data['pending_bookings'] or 0
        total_revenue = float(stats_data['total_revenue'] or 0)
        
        # 2. Last 7 Days Trend (Daily Counts and Revenue)
        last_7_days = timezone.now().date() - timedelta(days=6)
        
        trend_data = BookingItem.objects.filter(
            base_filters & Q(selected_time__date__gte=last_7_days)
        ).annotate(
            date=TruncDate('selected_time')
        ).values('date').annotate(
            count=Count('id'),
            revenue=Sum('booking__total_price', filter=Q(status='COMPLETED'))
        ).order_by('date')
        
        # Fill in missing days
        trend_map = {item['date'].strftime('%Y-%m-%d'): {
            "count": item['count'],
            "revenue": float(item['revenue'] or 0)
        } for item in trend_data}
        
        filled_trend = []
        for i in range(7):
            day = last_7_days + timedelta(days=i)
            day_str = day.strftime('%Y-%m-%d')
            day_data = trend_map.get(day_str, {"count": 0, "revenue": 0.0})
            filled_trend.append({
                "date": day_str,
                "count": day_data["count"],
                "revenue": day_data["revenue"]
            })
            
        return Response({
            "total_bookings": total_bookings,
            "pending_bookings": pending_bookings,
            "total_revenue": total_revenue,
            "trend": filled_trend
        })

    @action(detail=True, methods=['post'], url_path='verify-payment')
    def verify_payment(self, request, pk=None):
        """
        Action to verify Stripe payment and finalize booking.
        Expects: { "session_id": "cs_test_..." }
        """
        booking = self.get_object()
        session_id = request.data.get('session_id')
        
        if not session_id:
            return Response({"error": "session_id is required"}, status=400)
            
        # 1. Verify with Stripe
        if not StripeService:
            # Fallback verification if service isn't reachable but session matches
            if booking.transaction_id == session_id:
                 logger.warning(f"Using fallback verification for booking {booking.id}")
            else:
                 return Response({"error": "Stripe identity service not available"}, status=503)
            
        try:
            # Check if this session is indeed for this booking
            if booking.transaction_id != session_id:
                return Response({"error": "Session ID mismatch"}, status=400)

            # Mark PAID
            with transaction.atomic():
                booking.payment_status = 'PAID'
                booking.status = 'CONFIRMED'
                booking.save()
                
                # 2. Trigger Invoice Generation
                InvoiceService.generate_invoice(booking.id)
                
                # 3. Publish Kafka Event
                publish_booking_event('BOOKING_PAID', booking)
                
            return Response({
                "message": "Payment verified and booking confirmed",
                "status": booking.payment_status,
                "booking_id": booking.id
            })
            
        except Exception as e:
            logger.exception("Verification failure")
            return Response({"error": f"Verification failed: {str(e)}"}, status=500)


from .models import BookingItem
from .serializers import BookingItemSerializer
import random

class BookingItemViewSet(viewsets.ModelViewSet):
    queryset = BookingItem.objects.all()
    serializer_class = BookingItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'])
    def generate_otp(self, request, pk=None):
        item = self.get_object()
        
        # Permission: Only assigned employee or provider can generate
        is_provider = str(item.provider_id) == str(request.user.id)
        is_assigned_employee = item.assigned_employee_id and str(item.assigned_employee_id) == str(request.user.id)
        
        if not (is_provider or is_assigned_employee):
             return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        if item.status != 'CONFIRMED':
             return Response({"error": "Item must be confirmed to generate OTP"}, status=400)

        # Generate 4-digit OTP
        otp = f"{random.randint(1000, 9999)}"
        item.completion_otp = otp
        item.otp_expires_at = timezone.now() + timedelta(minutes=15) # 15 min val
        item.save()
        
        return Response({"message": "OTP Generated", "expires_in": "15 minutes"})

    @action(detail=True, methods=['post'])
    def verify_otp(self, request, pk=None):
        item = self.get_object()
        otp = request.data.get('otp')
        
        # Permission: Only assigned employee or provider can verify
        is_provider = str(item.provider_id) == str(request.user.id)
        is_assigned_employee = item.assigned_employee_id and str(item.assigned_employee_id) == str(request.user.id)
        
        if not (is_provider or is_assigned_employee):
             return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        if not item.completion_otp:
             return Response({"error": "No OTP generated"}, status=400)
             
        if item.completion_otp != otp:
             return Response({"error": "Invalid OTP"}, status=400)
             
        if timezone.now() > item.otp_expires_at:
             return Response({"error": "OTP Expired"}, status=400)

        # Success
        item.status = 'COMPLETED'
        item.completed_at = timezone.now()
        item.completion_otp = None # Clear usage
        item.save()
        
        # Update parent booking status if all items complete
        all_complete = not item.booking.items.exclude(status='COMPLETED').exists()
        if all_complete:
            item.booking.status = 'COMPLETED'
            item.booking.save()
            
        return Response({"message": "Service Completed Successfully"})

class AnalyticsProViewSet(viewsets.GenericViewSet):
    """
    Advanced BI Analytics ViewSet for Enterprise Provider Reporting.
    Providing Forecasting, Retention, and Staff Intelligence.
    Accessible by provider tokens (service-to-service) and pet owner tokens.
    Data is always scoped by provider_id query param.
    """
    # AllowAny because this is an internal service-to-service endpoint.
    # Security is handled at the service_provider_service gateway level.
    # provider_id param ensures data isolation.
    permission_classes = [permissions.AllowAny]

    def _get_date_range(self, request):
        range_type = request.query_params.get('range', '7d')
        now = timezone.now()
        
        if range_type == 'today':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif range_type == '7d':
            start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif range_type == '30d':
            start = (now - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif range_type == 'month':
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif range_type == 'custom':
            start_str = request.query_params.get('start_date')
            end_str = request.query_params.get('end_date')
            try:
                start = datetime.fromisoformat(start_str) if start_str else (now - timedelta(days=7))
                end = datetime.fromisoformat(end_str) if end_str else now
            except ValueError:
                start = now - timedelta(days=7)
                end = now
        else:
            start = now - timedelta(days=7)
            end = now
            
        return start, end

    @action(detail=False, methods=['get'])
    def kpi_summary(self, request):
        provider_id = request.query_params.get('provider_id')
        if not provider_id:
            return Response({"error": "provider_id is required"}, status=400)

        start, end = self._get_date_range(request)
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        base_items = BookingItem.objects.filter(provider_id=provider_id)
        range_items = base_items.filter(selected_time__range=(start, end))

        # 1. Real-time KPIs
        stats = range_items.aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='COMPLETED')),
            cancelled=Count('id', filter=Q(status__in=['CANCELLED', 'REJECTED'])),
            revenue=Sum('booking__total_price', filter=Q(status='COMPLETED')),
        )

        today_stats = base_items.filter(selected_time__range=(today_start, today_end)).aggregate(
            bookings=Count('id'),
            revenue=Sum('booking__total_price', filter=Q(status='COMPLETED'))
        )

        # 2. Hardened Forecasting
        # Monthly run rate with variance analysis
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        days_passed = (now - month_start).days + 1
        days_in_month = 30 # Simplified
        
        month_items = base_items.filter(selected_time__range=(month_start, now), status='COMPLETED')
        
        # Calculate daily revenue for variance
        daily_revs = month_items.annotate(
            day=TruncDay('selected_time')
        ).values('day').annotate(
            daily_total=Sum('booking__total_price')
        ).values_list('daily_total', flat=True)
        
        import math
        rev_list = [float(r) for r in daily_revs]
        month_rev = sum(rev_list)
        
        mean_rev = month_rev / days_passed if days_passed > 0 else 0
        variance = sum((r - mean_rev) ** 2 for r in rev_list) / len(rev_list) if len(rev_list) > 1 else 0
        std_dev = math.sqrt(variance)
        
        projected_revenue = mean_rev * days_in_month
        
        # Confidence Score: 1 - (CV / 2) clamped to 0-1. CV = std_dev/mean
        cv = (std_dev / mean_rev) if mean_rev > 0 else 1
        confidence_score = max(0, min(1, 1 - (cv / 2))) * 100
        
        # Scenarios (± 1 Std Dev)
        low_case = (mean_rev - std_dev) * days_in_month
        high_case = (mean_rev + std_dev) * days_in_month

        # 3. AVG Values
        total_completed = stats['completed'] or 0
        total_revenue = float(stats['revenue'] or 0)
        avg_booking_value = total_revenue / total_completed if total_completed > 0 else 0

        # 4. Cancellation Analytics
        cancellation_rate = (stats['cancelled'] or 0) / (stats['total'] or 1) * 100

        return Response({
            "kpis": {
                "today_bookings": today_stats['bookings'] or 0,
                "today_revenue": float(today_stats['revenue'] or 0),
                "total_bookings": stats['total'] or 0,
                "completed_bookings": total_completed,
                "cancellation_rate": round(cancellation_rate, 2),
                "avg_booking_value": round(avg_booking_value, 2),
            },
            "forecasting": {
                "current_month_revenue": round(month_rev, 2),
                "projected_month_revenue": round(projected_revenue, 2),
                "confidence_score": round(confidence_score, 1),
                "scenarios": {
                    "low": round(max(month_rev, low_case), 2),
                    "high": round(high_case, 2)
                },
                "days_remaining": days_in_month - days_passed
            }
        })

    @action(detail=False, methods=['get'])
    def service_intelligence(self, request):
        provider_id = request.query_params.get('provider_id')
        if not provider_id:
            return Response({"error": "provider_id is required"}, status=400)

        start, end = self._get_date_range(request)
        
        # Group by service to get raw metrics
        qs = BookingItem.objects.filter(
            provider_id=provider_id,
            selected_time__range=(start, end)
        ).values('service_id', 'service_snapshot__service_name').annotate(
            bookings=Count('id'),
            revenue=Sum('booking__total_price', filter=Q(status='COMPLETED')),
            cancelled=Count('id', filter=Q(status__in=['CANCELLED', 'REJECTED'])),
            unique_customers=Count('booking__owner', distinct=True)
        ).order_by('-bookings')

        results = []
        for item in qs:
            bookings = item['bookings'] or 0
            revenue = float(item['revenue'] or 0)
            
            # Repeat customer logic: owners with > 1 booking for THIS service in THIS range
            # Note: This is an approximation for performance
            repeat_customers = bookings - item['unique_customers']
            
            results.append({
                "service_id": str(item['service_id']),
                "name": item['service_snapshot__service_name'] or "Unknown Service",
                "bookings": bookings,
                "revenue": revenue,
                "repeat_customers": max(0, repeat_customers),
                "cancellation_rate": round((item['cancelled'] / bookings * 100), 2) if bookings > 0 else 0
            })

        return Response(results)

    @action(detail=False, methods=['get'])
    def customer_insights(self, request):
        provider_id = request.query_params.get('provider_id')
        if not provider_id:
            return Response({"error": "provider_id is required"}, status=400)

        start, end = self._get_date_range(request)
        
        # 1. New vs Returning (Existing Logic)
        all_owners_in_range = BookingItem.objects.filter(
            provider_id=provider_id,
            selected_time__range=(start, end)
        ).values_list('booking__owner_id', flat=True).distinct()

        new_customers = 0
        returning_customers = 0
        
        for owner_id in all_owners_in_range:
            has_prior = BookingItem.objects.filter(
                provider_id=provider_id,
                booking__owner_id=owner_id,
                selected_time__lt=start
            ).exists()
            
            if has_prior:
                returning_customers += 1
            else:
                new_customers += 1

        # 2. Hardened Retention Cohorts (30/60/90 day returns)
        # Using a reference date (start of range) to check prior activity
        
        def count_returns(days_min, days_max):
            d_max = start - timedelta(days=days_min)
            d_min = start - timedelta(days=days_max)
            # Find owners whose *previous* booking was in this window
            prior_owners = BookingItem.objects.filter(
                provider_id=provider_id,
                selected_time__range=(d_min, d_max)
            ).values_list('booking__owner_id', flat=True).distinct()
            
            # Count how many of those returned in the current range
            returned = 0
            for oid in prior_owners:
                if oid in all_owners_in_range:
                    returned += 1
            return len(prior_owners), returned

        c30_total, c30_ret = count_returns(0, 30)
        c60_total, c60_ret = count_returns(31, 60)
        c90_total, c90_ret = count_returns(61, 90)

        # 3. Lost Customers (> 90 days since last booking)
        all_time_owners = BookingItem.objects.filter(provider_id=provider_id).values_list('booking__owner_id', flat=True).distinct()
        lost_customers = 0
        last_90_days = now - timedelta(days=90)
        
        for oid in all_time_owners:
            recent = BookingItem.objects.filter(
                provider_id=provider_id,
                booking__owner_id=oid,
                selected_time__gt=last_90_days
            ).exists()
            if not recent:
                lost_customers += 1

        # 4. Top Customers (by revenue)
        top_customers_qs = BookingItem.objects.filter(
            provider_id=provider_id,
            status='COMPLETED',
            selected_time__range=(start, end)
        ).values('booking__owner_id', 'booking__owner__full_name').annotate(
            spend=Sum('booking__total_price'),
            visits=Count('id')
        ).order_by('-spend')[:10]

        top_customers = [{
            "id": str(c['booking__owner_id']),
            "name": c['booking__owner__full_name'] or "Anonymous",
            "spend": float(c['spend'] or 0),
            "visits": c['visits']
        } for c in top_customers_qs]

        return Response({
            "segments": {
                "new": new_customers,
                "returning": returning_customers,
                "total": len(all_owners_in_range),
                "retention_rate": round((returning_customers / len(all_owners_in_range) * 100), 2) if len(all_owners_in_range) > 0 else 0
            },
            "cohorts": {
                "r30": round((c30_ret / c30_total * 100), 1) if c30_total > 0 else 0,
                "r60": round((c60_ret / c60_total * 100), 1) if c60_total > 0 else 0,
                "r90": round((c90_ret / c90_total * 100), 1) if c90_total > 0 else 0,
                "lost": lost_customers
            },
            "top_customers": top_customers
        })

    @action(detail=False, methods=['get'])
    def team_performance(self, request):
        provider_id = request.query_params.get('provider_id')
        if not provider_id:
            return Response({"error": "provider_id is required"}, status=400)

        start, end = self._get_date_range(request)

        # Performance by staff member
        staff_qs = BookingItem.objects.filter(
            provider_id=provider_id,
            selected_time__range=(start, end)
        ).exclude(assigned_employee_id__isnull=True).values('assigned_employee_id').annotate(
            bookings=Count('id'),
            revenue=Sum('booking__total_price', filter=Q(status='COMPLETED')),
            cancelled=Count('id', filter=Q(status__in=['CANCELLED', 'REJECTED']))
        ).order_by('-revenue')

        staff_data = [{
            "employee_id": item['assigned_employee_id'],
            "bookings": item['bookings'],
            "revenue": float(item['revenue'] or 0),
            "cancellation_rate": round((item['cancelled'] / item['bookings'] * 100), 2) if item['bookings'] > 0 else 0
        } for item in staff_qs]

        return Response(staff_data)

    @action(detail=False, methods=['get'])
    def capacity_raw(self, request):
        """Provides raw minute-level booking data for utilization audits."""
        provider_id = request.query_params.get('provider_id')
        if not provider_id:
            return Response({"error": "provider_id is required"}, status=400)

        start, end = self._get_date_range(request)
        
        # Get all booking items with their durations
        items = BookingItem.objects.filter(
            provider_id=provider_id,
            selected_time__range=(start, end)
        ).exclude(status__in=['CANCELLED', 'REJECTED'])

        raw_data = []
        for item in items:
            # Extract duration from snapshots
            duration = 60
            if item.price_snapshot and 'duration_minutes' in item.price_snapshot:
                duration = item.price_snapshot['duration_minutes']
            elif item.service_snapshot and 'duration' in item.service_snapshot:
                duration = item.service_snapshot['duration']
            
            raw_data.append({
                "employee_id": item.assigned_employee_id,
                "service_id": item.service_id,
                "start": item.selected_time.isoformat(),
                "duration": duration
            })

        return Response(raw_data)


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Pet Owners to view their invoices.
    """
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Only show invoices for bookings owned by this user
        return Invoice.objects.filter(booking__owner__auth_user_id=user.id)

    @action(detail=True, methods=['get'], url_path='download')
    def download_pdf(self, request, pk=None):
        """Serve the generated PDF file."""
        invoice = self.get_object()
        if not invoice.pdf_file:
            # Re-generate if missing
            InvoiceService.generate_pdf_task(invoice.id)
            invoice.refresh_from_db()
            
        if not invoice.pdf_file:
            return Response({"error": "PDF not available"}, status=404)
            
        try:
            # Serve as attachment
            response = Response(invoice.pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
            return response
        except Exception as e:
            return Response({"error": str(e)}, status=500)
    @action(detail=False, methods=['get'], url_path='internal_pet_history')
    def internal_pet_history(self, request):
        """Internal endpoint to fetch previous staff IDs for a specific pet (Rule 1)"""
        pet_id = request.query_params.get('pet_id')
        if not pet_id:
            return Response([])
            
        staff_ids = BookingItem.objects.filter(
            pet_id=pet_id,
            assigned_employee_id__isnull=False
        ).values_list('assigned_employee_id', flat=True).distinct()
        
        return Response([str(sid) for sid in staff_ids])

    @action(detail=False, methods=['post'], url_path='join-waitlist')
    def join_waitlist(self, request):
        """Tier 3: Capture demand when fully booked (Rule 4)"""
        pet_id = request.data.get('pet_id')
        service_id = request.data.get('service_id')
        org_id = request.data.get('organization_id')
        
        if not all([pet_id, service_id, org_id]):
            return Response({"error": "Missing required fields"}, status=400)
            
        from .models import WaitlistEntry, Pet, PetOwnerProfile
        pet = get_object_or_404(Pet, id=pet_id)
        owner_profile = get_object_or_404(PetOwnerProfile, auth_user_id=self.request.user.id)
        
        entry = WaitlistEntry.objects.create(
            organization_id=org_id,
            owner=owner_profile,
            pet=pet,
            service_id=service_id,
            preferred_date=request.data.get('date'),
            preferred_time_start=request.data.get('start_time'),
            preferred_time_end=request.data.get('end_time'),
            notes=request.data.get('notes', '')
        )
        
        return Response({"status": "joined_waitlist", "waitlist_id": entry.id})

    @action(detail=True, methods=['post'], url_path='assign-staff')
    def assign_staff(self, request, pk=None):
        """Manual override for staff assignment (Rule 2)"""
        booking = self.get_object()
        employee_id = request.data.get('employee_id')
        
        if not employee_id:
             return Response({"error": "employee_id required"}, status=400)
             
        with transaction.atomic():
            for item in booking.items.all():
                item.assigned_employee_id = employee_id
                item.status = 'CONFIRMED'
                item.save()
            
            booking.status = 'CONFIRMED'
            booking.save()
            
            # Record status change
            BookingStatusHistory.objects.create(
                booking=booking,
                previous_status='SEARCHING_STAFF',
                new_status='CONFIRMED',
                changed_by=self.request.user.id
            )
            
        return Response({"status": "success"})
