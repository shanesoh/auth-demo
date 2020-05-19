# Auth demo using kong + kong-oidc + keycloak + some mock services

## Getting started

Run `docker-compose up` to start all the necessary services, including mock services `k2o` and `c3n`.

Wait for at least a couple of minutes as decK (declarative configuration tool for Kong) will wait a while before starting up.


## Usage

### Accessing services directly (not via Kong)
Start a local browser and visit `k2o.localhost` and `c3n.localhost` to access the services directly. As these services are not accessed via Kong, the user will not be redirected to Keycloak for authentication and thus no access token will be forwarded to the services.

In `k2o.localhost`, you can try accessing the `/whoami` endpoint. You should get a 403 Forbidden as no access token is passed (user hasn't authenticated yet).

### Accessing upstream services via Kong

Browse to `k2o.kong.localhost` and `c3n.kong.localhost` to access the services through the Kong gateway. 

You will be redirected to Keycloak to log in. You may use the `admin:admin` credentials (for admin) or the `user:user` credentials (or create other users yourself (see below on accessing Keycloak admin)).

### k2o
`k2o` uses OPA to control access to its endpoints. OPA policies can be found in `./compose/k2o/policy`. Note that any variables defined in OPA will be in the OPA response. In this case, we want OPA to return both the raw access token and the decoded claims.

#### `/whoami`
Try accessing the `/whoami` endpoint. If you're logged in as `user`, you will get a 200 response. If you are logged in as `admin`, you will get a 403 Forbidden instead.


#### `/profile/{profile_id}`
The `/profile` endpoint is public so anyone can access it. In fact, it does not use the `check_opa_authz` dependency and therefore does not expect an access token. 

Therefore, this endpoint will still work if you access it via `k2o.localhost/profile` (i.e. not through Kong).


#### `/lookupSsn`
This endpoint calls `c3n` via kong. The user's access token is passed to k2o via kong, k2o then uses that access token to call c3n. 

The access token (in its undecoded form) is returned by OPA so we can pass it on to c3n.

Note that currently c3n does not use OPA (or implement any kind of authz) so this passing of token would seem redundant.


### c3n
A dummy service that exists solely to mock inter-service calls from k2o.


## Administration

### Keycloak
Visit `https://keycloak.localhost` and login with `admin:admin`.

You should try creating a new user and accessing the proxied mock services with the created user's credentials.

### Konga
Konga is a GUI for Kong's admin API. You probably don't need this but if you're curious to see how Kong was configured, visit `localhost:1337`, then create a new connection (name: <anything>: kong admin url: `http://kong:8001`).
