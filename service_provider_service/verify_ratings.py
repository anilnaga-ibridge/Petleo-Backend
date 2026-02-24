
import os
import django
import uuid

# Setup Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'service_provider_service.settings'
django.setup()

from service_provider.models import ServiceProvider, VerifiedUser, ProviderRating
from django.db import transaction

def test_rating_logic():
    print("--- Testing Rating System Logic ---")
    
    # 1. Create a dummy provider
    user_id = uuid.uuid4()
    v_user = VerifiedUser.objects.create(
        auth_user_id=user_id,
        full_name="Testing Provider",
        email=f"test_{user_id.hex[:6]}@example.com",
        role="organization"
    )
    provider = ServiceProvider.objects.create(verified_user=v_user, profile_status='active', is_fully_verified=True)
    
    print(f"Created Provider: {provider.id} ({provider.verified_user.full_name})")
    print(f"Initial Stats: Avg={provider.average_rating}, Total={provider.total_ratings}")

    # 2. Simulate ratings from different customers
    ratings = [5, 4, 3, 5, 5]
    customer_ids = [uuid.uuid4() for _ in range(len(ratings))]

    for i, r_val in enumerate(ratings):
        cust_id = customer_ids[i]
        print(f"\nSubmitting Rating {i+1}: {r_val} stars from customer {cust_id}")
        
        with transaction.atomic():
            # Simulate RatingSubmitView logic
            ProviderRating.objects.create(
                customer_id=cust_id,
                provider=provider,
                rating=r_val,
                review=f"Review for {r_val} stars"
            )
            
            # Recalculate stats
            from django.db.models import Avg, Count
            stats = ProviderRating.objects.filter(provider=provider).aggregate(
                avg=Avg('rating'),
                count=Count('id')
            )
            
            provider.average_rating = round(stats['avg'] or 0.0, 1)
            provider.total_ratings = stats['count'] or 0
            provider.save(update_fields=['average_rating', 'total_ratings'])
            
            print(f"Updated Stats: Avg={provider.average_rating}, Total={provider.total_ratings}")

    expected_avg = round(sum(ratings) / len(ratings), 1)
    print(f"\nVerification Results:")
    print(f"Expected Avg: {expected_avg}")
    print(f"Actual Avg: {provider.average_rating}")
    print(f"Total Ratings: {provider.total_ratings}")
    
    if provider.average_rating == expected_avg and provider.total_ratings == len(ratings):
        print("\n✅ Rating Calculation Success!")
    else:
        print("\n❌ Rating Calculation Failed!")

    # Cleanup (optional, but good for repeatability)
    # v_user.delete() 

if __name__ == "__main__":
    test_rating_logic()
