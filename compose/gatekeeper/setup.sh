#!/bin/sh

# Sets up the applications realm if it does not exist, then
# Sets up a client if it does not exist, then
# Writes client's client_secret to stdout

keycloak_url=${KEYCLOAK_URL:-https://keycloak.localhost}
keycloak_realm=${KEYCLOAK_REALM:-applications}
keycloak_username=${KEYCLOAK_USERNAME:-admin}
keycloak_password=${KEYCLOAK_PASSWORD:-password}

if [ -z $GATEKEEPER_CLIENT_ID ]; then
    echo ">>> GATEKEEPER_CLIENT_ID must be set!"
    exit 1
fi

# Get the token (default: expires in  1 minute)
token=$(curl -X POST -H 'Accept: application/json' -sSk "$keycloak_url/auth/realms/master/protocol/openid-connect/token" -d "client_id=admin-cli&password=${keycloak_password}&username=${keycloak_username}&grant_type=password" | cut -d '"' -f4)

# Wait up to 30s until applications realm is created
for i in $(seq 30); do
    return_code=$(curl -X GET -o /dev/null -H "Content-Type: application/json" -H "Authorization: Bearer $token" -w '%{http_code}' -sSk "$keycloak_url/auth/admin/realms/$keycloak_realm")
    [ "$return_code" -eq "200" ] && break
    sleep 1;
done

# Create get id of client first
client_id=$(curl -X GET -H "Content-Type: application/json" -H "Authorization: Bearer $token" -sSk "$keycloak_url/auth/admin/realms/$keycloak_realm/clients" | jq -r ".[] | select(.clientId == \"${GATEKEEPER_CLIENT_ID}\") | .id")

# Get client's id
if [ -z $client_id ]; then
    # Create a client
    curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer $token" -sSk "$keycloak_url/auth/admin/realms/$keycloak_realm/clients" --data-binary @- >/dev/null <<EOF
{
  "clientId": "${GATEKEEPER_CLIENT_ID}",
  "name": "${GATEKEEPER_CLIENT_ID}",
  "enabled": true,
  "baseUrl": "https://${GATEKEEPER_CLIENT_ID}.localhost",
  "redirectUris": ["https://${GATEKEEPER_CLIENT_ID}.localhost/*"]
}
EOF

    # Get the id again
    client_id=$(curl -X GET -H "Content-Type: application/json" -H "Authorization: Bearer $token" -sSk "$keycloak_url/auth/admin/realms/$keycloak_realm/clients" | jq -r ".[] | select(.clientId == \"${GATEKEEPER_CLIENT_ID}\") | .id")

    # Add the Audience mapper for this client (aud claim should be the same as client_id)
    curl -H "Content-Type: application/json" -H "Authorization: Bearer $token" -sSk "$keycloak_url/auth/admin/realms/$keycloak_realm/clients/$client_id/protocol-mappers/models" --data-binary @- >/dev/null <<EOF
{
  "protocol": "openid-connect",
  "config": {
    "id.token.claim": "false",
    "access.token.claim": "true",
    "included.client.audience": "${GATEKEEPER_CLIENT_ID}"
  },
  "name": "${GATEKEEPER_CLIENT_ID}-aud",
  "protocolMapper": "oidc-audience-mapper"
}
EOF
fi

# Get client's secret
curl -X GET -H "Content-Type: application/json" -H "Authorization: Bearer $token" -sSk "$keycloak_url/auth/admin/realms/$keycloak_realm/clients/$client_id/client-secret" | jq -r '.value'
