Write-Host "Starting Kong setup..."

$KONG = "http://localhost:8001"

# ---------------------------
# 1. SERVICES
# ---------------------------

Write-Host "Creating Auth Service..."
curl.exe -i -X POST "$KONG/services" --data "name=auth-service" --data "url=http://auth_service:8000"

Write-Host "Creating Provider Service..."
curl.exe -i -X POST "$KONG/services" --data "name=provider-service" --data "url=http://service_provider_service:8000"

Write-Host "Creating Super Admin Service..."
curl.exe -i -X POST "$KONG/services" --data "name=super-admin-service" --data "url=http://super_admin_service:8000"


# ---------------------------
# 2. ROUTES
# ---------------------------

Write-Host "Creating Auth Route..."
curl.exe -i -X POST "$KONG/services/auth-service/routes" --data "name=auth-route" --data "paths[]=/auth"

Write-Host "Creating Provider Route..."
curl.exe -i -X POST "$KONG/services/provider-service/routes" --data "name=provider-route" --data "paths[]=/provider"

Write-Host "Creating Super Admin Route..."
curl.exe -i -X POST "$KONG/services/super-admin-service/routes" --data "name=super-admin-route" --data "paths[]=/superadmin"


# ---------------------------
# 3. ENABLE CORS
# ---------------------------

Write-Host "Enabling CORS for Auth..."
curl.exe -i -X POST "$KONG/services/auth-service/plugins" --data "name=cors" --data "config.origins=*" --data "config.methods=GET,POST,PUT,DELETE,OPTIONS" --data "config.headers=*" --data "config.credentials=true"

Write-Host "Enabling CORS for Provider..."
curl.exe -i -X POST "$KONG/services/provider-service/plugins" --data "name=cors" --data "config.origins=*" --data "config.methods=GET,POST,PUT,DELETE,OPTIONS" --data "config.headers=*" --data "config.credentials=true"

Write-Host "Enabling CORS for Super Admin..."
curl.exe -i -X POST "$KONG/services/super-admin-service/plugins" --data "name=cors" --data "config.origins=*" --data "config.methods=GET,POST,PUT,DELETE,OPTIONS" --data "config.headers=*" --data "config.credentials=true"


# ---------------------------
# DONE
# ---------------------------

Write-Host "Kong setup complete!"
Write-Host "Test your endpoints now:"
Write-Host "Auth:        http://localhost:8000/auth/"
Write-Host "Provider:    http://localhost:8000/provider/"
Write-Host "Super Admin: http://localhost:8000/superadmin/"
