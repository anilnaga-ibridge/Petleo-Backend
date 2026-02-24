from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate
from .models import Booking, BookingStatusHistory, BookingItem
from .serializers import BookingSerializer, BookingStatusHistorySerializer
from customers.models import PetOwnerProfile
from pets.permissions import IsOwner
import requests
from django.db import transaction, IntegrityError
from datetime import datetime, timedelta
from .engines.router import BookingRouter

class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing bookings and their lifecycle.
    """
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        provider_id_param = self.request.query_params.get('provider_id')
        from django.db.models import Q

        queryset = Booking.objects.all()
        filters = Q()
        
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
                resolve_url = f"http://localhost:8002/api/provider/resolve-details/?service_id={serializer.validated_data['service_id']}&facility_id={serializer.validated_data['facility_id']}"
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
                return booking
                
                # Initial history record
                BookingStatusHistory.objects.create(
                    booking=booking,
                    previous_status='NONE',
                    new_status='PENDING',
                    changed_by=self.request.user.id
                )
                return booking # Return the header
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

            if selected_time != item.selected_time.isoformat():
                provider_id = item.provider_id
            try:
                # 1. Validate slot availability
                date_str = selected_time.split('T')[0] if 'T' in selected_time else selected_time.split(' ')[0]
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
                    
                if time_str not in available_slots:
                    raise ValidationError(f"Selected slot {time_str} is no longer available.")
                    
                # 2. Re-assign employee if organization
                assign_url = f"http://localhost:8002/api/provider/availability/{provider_id}/assign-employee/"
                assign_resp = requests.post(assign_url, json={"selected_time": selected_time}, timeout=5)
                
                assigned_employee_id = instance.assigned_employee_id
                if assign_resp.status_code == 200:
                    assigned_employee_id = assign_resp.json().get('employee_id')
                elif assign_resp.status_code == 400:
                     raise ValidationError(assign_resp.json().get('error', 'Employee assignment failed'))

                # 3. Save with transaction
                with transaction.atomic():
                    serializer.save(assigned_employee_id=assigned_employee_id)
                    
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
            # provider_id in items is the ServiceProvider UUID, which maps to Clinic.provider_id
            provider_id = str(item.provider_id)
            employee_id = str(item.assigned_employee_id) if item.assigned_employee_id else None

            if not employee_id:
                logger.warning(f"[VetSync] No assigned employee for booking {booking.id}, skipping sync")
                return

            # Build appointment payload
            selected_time = item.selected_time
            start_time_str = selected_time.strftime('%H:%M') if selected_time else '09:00'
            appointment_date = selected_time.date().isoformat() if selected_time else None

            payload = {
                'booking_id': str(booking.id),
                'clinic_id': provider_id,
                'doctor_auth_id': employee_id,
                'pet_owner_auth_id': str(booking.owner.auth_user_id) if booking.owner else '',
                'pet_external_id': str(item.pet_id) if item.pet_id else '',
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
            status__in=['PENDING', 'CONFIRMED'],
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
        Query Params: provider_id
        """
        provider_id = request.query_params.get('provider_id')
        if not provider_id:
            return Response({"error": "provider_id is required"}, status=400)
            
        # Verify permission (User must be the provider or an employee of the provider)
        # For simplicity in this microservice call, we trust the inter-service auth if present,
        # OR we check if the requesting user is linked to the provider.
        # Since this is likely called by Service Provider Service via server-to-server, 
        # we might need to relax strict user checks if it's a service token, 
        # but here we rely on the user context passed through headers.
        
        from django.db.models import Count
        from django.db.models.functions import TruncDate
        from datetime import timedelta
        
        # 1. Total Counts
        from .models import BookingItem
        total_bookings = BookingItem.objects.filter(provider_id=provider_id).count()
        pending_bookings = BookingItem.objects.filter(provider_id=provider_id, status='PENDING').count()
        
        # 2. Last 7 Days Trend
        last_7_days = timezone.now().date() - timedelta(days=6)
        
        trend_data = BookingItem.objects.filter(
            provider_id=provider_id,
            selected_time__date__gte=last_7_days
        ).annotate(
            date=TruncDate('selected_time')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        # Fill in missing days
        trend_map = {item['date'].strftime('%Y-%m-%d'): item['count'] for item in trend_data}
        filled_trend = []
        for i in range(7):
            day = last_7_days + timedelta(days=i)
            day_str = day.strftime('%Y-%m-%d')
            filled_trend.append({
                "date": day_str,
                "count": trend_map.get(day_str, 0)
            })
            
        return Response({
            "total_bookings": total_bookings,
            "pending_bookings": pending_bookings,
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
