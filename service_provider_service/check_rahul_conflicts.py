import requests
from datetime import date

def check_rahul_conflicts():
    employee_id = '5c3b54b9-aa99-441d-8598-df3aea0b59fd'
    target_date = date(2026, 2, 25)
    date_str = target_date.strftime('%Y-%m-%d')
    
    print(f"Checking conflicts for Rahul ({employee_id}) on {date_str}")
    
    # 1. Customer Service Bookings
    try:
        url = f"http://localhost:8005/api/pet-owner/bookings/bookings/internal_employee_bookings/"
        params = {"employee_id": employee_id, "date": date_str}
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            print(f"Customer Service Bookings: {response.json()}")
        else:
            print(f"Failed to fetch customer bookings: {response.status_code}")
    except Exception as e:
        print(f"Error fetching customer bookings: {e}")

    # 2. Veterinary Service Appointments
    try:
        url = f"http://localhost:8004/api/veterinary/appointments/internal_doctor_appointments/"
        params = {"doctor_auth_id": employee_id, "date": date_str}
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            print(f"Veterinary Service Appointments: {response.json()}")
        else:
            print(f"Failed to fetch medical appointments: {response.status_code}")
    except Exception as e:
        print(f"Error fetching medical appointments: {e}")

if __name__ == "__main__":
    check_rahul_conflicts()
