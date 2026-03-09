import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
django.setup()

from bookings.models import BookingItem, BookingStatusHistory
from bookings.views import BookingViewSet

def main():
    items = BookingItem.objects.filter(id='de2d07e5-d49b-4f8d-b29b-0414082e056a')
    count = 0
    for i in items:
        if i.service_snapshot and i.service_snapshot.get('is_medical'):
            b = i.booking
            if b.status != 'CONFIRMED':
                b.status = 'CONFIRMED'
                b.save()
                BookingStatusHistory.objects.create(
                    booking=b, 
                    previous_status='PENDING', 
                    new_status='CONFIRMED', 
                    changed_by=b.owner.auth_user_id if hasattr(b.owner, 'auth_user_id') else '00000000-0000-0000-0000-000000000000'
                )
            
            print(f"Syncing booking {b.id} for pet {i.pet.name if i.pet else 'Unknown'}")
            try:
                import requests as http_requests
                # Extract payload building logic to trace it
                b_item = i
                pet = b_item.pet
                owner = b.owner
                selected_time = b_item.selected_time
                start_time_str = selected_time.strftime('%H:%M') if selected_time else '09:00'
                appointment_date = selected_time.date().isoformat() if selected_time else None
                clinic_auth_id = str(b_item.provider_auth_id) if b_item.provider_auth_id else str(b_item.provider_id)
                employee_id = str(b_item.assigned_employee_id) if b_item.assigned_employee_id else None

                payload = {
                    'booking_id': str(b.id),
                    'clinic_id': clinic_auth_id,
                    'doctor_auth_id': employee_id,
                    'pet_owner_auth_id': str(owner.auth_user_id) if owner else '',
                    'pet_external_id': str(pet.id) if pet else '',
                    'pet_name': pet.name if pet else 'Online Pet',
                    'species': pet.species if pet else 'DOG',
                    'breed': pet.breed if pet else '',
                    'gender': pet.gender if pet else 'MALE',
                    'date_of_birth': pet.date_of_birth.isoformat() if pet and pet.date_of_birth else None,
                    'weight_kg': str(pet.weight_kg) if pet and pet.weight_kg else '0',
                    'owner_name': owner.full_name if owner else 'Online Pet Owner',
                    'owner_phone': owner.phone_number if owner else '',
                    'owner_email': owner.email if owner else '',
                    'service_id': str(b_item.facility_id) if b_item.facility_id else str(b_item.service_id),
                    'appointment_date': appointment_date,
                    'start_time': start_time_str,
                    'consultation_type': b_item.service_snapshot.get('consultation_type', ''),
                    'consultation_fee': b_item.service_snapshot.get('price', '0.00'),
                    'notes': b.notes or '',
                }
                
                resp = http_requests.post('http://localhost:8004/api/veterinary/internal/create-online-appointment/', json=payload, timeout=5)
                if resp.status_code != 200 and resp.status_code != 201:
                    with open("error_dump.html", "w") as f:
                        f.write(resp.text)
                    print(f"Dumped error to error_dump.html (Status {resp.status_code})")
                else:
                    count += 1
                    i.status = 'CONFIRMED'
                    i.save()
            except Exception as e:
                print(f"Failed to sync {b.id}: {e}")
                
    print(f"Total synced: {count}")

if __name__ == "__main__":
    main()
