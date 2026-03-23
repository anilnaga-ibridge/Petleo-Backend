from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from .models import Booking, BookingStatusHistory, BookingItem
from .serializers import BookingSerializer, BookingStatusHistorySerializer
from customers.models import PetOwnerProfile
from pets.permissions import IsOwner
import requests
from django.db import transaction, IntegrityError
from datetime import datetime, timedelta
from .services import SlotLockService, AvailabilityCacheService
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
                booking = Booking.objects.create(
                    owner=owner_profile,
                    status='PENDING',
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
                    assigned_employee_id=employee_id,
                    service_snapshot=service_snapshot,
                    price_snapshot=price_snapshot,
                    status='PENDING'
                )
                
                BookingStatusHistory.objects.create(
                    booking=booking,
                    previous_status='NONE',
                    new_status='PENDING',
                    changed_by=self.request.user.id
                )

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
