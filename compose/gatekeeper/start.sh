#!/bin/sh

NAME=keycloak-gatekeeper
KEYCLOAK_VERSION=9.0.2
GOOS=linux
GOARCH=amd64

command -v curl || apk add --no-cache ca-certificates curl tar bash
command -v jq || curl -o /bin/jq -L https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64 && chmod +x /bin/jq
command -v wait-for-it.sh || curl -o /bin/wait-for-it.sh https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh && chmod +x /bin/wait-for-it.sh

# Setup gatekeeper
[ -f /opt/keycloak-gatekeeper ] || curl -fsSL "https://downloads.jboss.org/keycloak/$KEYCLOAK_VERSION/gatekeeper/$NAME-$GOOS-$GOARCH.tar.gz" | tar -xz -C /tmp && chmod +x /tmp/$NAME

# Add keycloak's certificate inside container
update-ca-certificates

# Wait for keycloak to be ready (use a direct connection to the container to
#   test, because traefik (keycloak.localhost) comes up way before the service
#   is ready
wait-for-it.sh -t 60 keycloak:8443

# Sets up this client with keycloak
client_secret=$(/gatekeeper/setup.sh)

echo ">>> Using client_secret=|$client_secret|"
exec /tmp/keycloak-gatekeeper --config /gatekeeper/config.yml --client-secret=$client_secret
