# #!/bin/sh
# set -e

# KONG=http://kong:8001

# echo "Waiting for Kong Admin API..."
# until curl -s $KONG/status >/dev/null; do
#   sleep 2
# done
# echo "Kong is up."

# create_service() {
#   NAME="$1"
#   URL="$2"
#   PATH="$3"

#   echo "Creating service: $NAME -> $URL"
#   curl -s -o /dev/null -w "%{http_code}\n" -X POST $KONG/services \
#     --data name="$NAME" --data url="$URL" | grep -E "200|201" >/dev/null || true

#   echo "Creating/ensuring route for: $NAME at path $PATH"
#   curl -s -o /dev/null -w "%{http_code}\n" -X POST $KONG/services/$NAME/routes \
#     --data "paths[]=$PATH" | grep -E "200|201" >/dev/null || true

#   echo "Enabling CORS for $NAME"
#   curl -s -o /dev/null -w "%{http_code}\n" -X POST $KONG/services/$NAME/plugins \
#     --data "name=cors" \
#     --data "config.origins=http://localhost:3000,https://your-frontend-domain.com" \
#     --data "config.methods=GET,POST,PUT,DELETE,OPTIONS" \
#     --data "config.credentials=true" \
#     --data "config.max_age=3600" | grep -E "200|201" >/dev/null || true

#   echo "Enabling basic rate limiting for $NAME"
#   curl -s -o /dev/null -w "%{http_code}\n" -X POST $KONG/services/$NAME/plugins \
#     --data "name=rate-limiting" \
#     --data "config.minute=600" \
#     --data "config.policy=local" | grep -E "200|201" >/dev/null || true
# }

# # Map each Django service
# create_service auth_service            http://auth_service:8000            /auth
# create_service service_provider_service http://service_provider_service:8002 /serviceprovider
# create_service super_admin_service      http://super_admin_service:8003      /superadmin

# echo "Kong bootstrap complete."
