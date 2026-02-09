#!/bin/bash

echo "🚀 Starting Full Sync from Auth_Service (Registration Table) to provider_db..."

# Get all user IDs from Auth_Service
echo "  Fetching all users from Auth_Service..."
USERS=$(psql -U petleo -d Auth_Service -t -A -c "SELECT id, email, full_name, phone_number FROM users_user;")

while IFS='|' read -r id email name phone; do
    if [[ -z "$id" ]]; then continue; fi
    
    echo "  Syncing user: $email ($id)"
    
    # Update VerifiedUser in provider_db
    # We use -q for quiet and --command
    psql -U petleo -d provider_db -q -c "UPDATE verified_users SET full_name = '$name', email = '$email', phone_number = '$phone' WHERE auth_user_id = '$id';"
    
done <<< "$USERS"

echo "✅ Full Sync Complete!"
