# Auth demo using kong + kong-oidc + keycloak + some mock services

## Getting started

Run `docker-compose up` to start all the necessary services, including mock services `k2o` and `c3n`.


## Usage

Start a local browser and visit `k2o.localhost` and `c3n.localhost` to access the services directly.

Browse to `kong.localhost` to access the Kong gateway. You should see "no Route matched with those values" returned by the gateway because it's not proxying any service at that host.

Browse to `k2o.kong.localhost` and `c3n.kong.localhost` to access the services through the Kong gateway. 
You will be redirected to Keycloak to log in. You may use the `admin:admin` credentials or a user credentials that you will have to create yourself (see below on accessing Keycloak admin)

**Try using the `k2o.kong.localhost/lookupSsn` endpoint** (via the Swagger UI perhaps). This API calls `c3n` via kong. The user's access token is passed to k2o via kong, k2o then uses that access token to call c3n. See `compose/k2o/main.py` for more details.


## Administration

### Keycloak
Visit `https://keycloak.localhost` and login with `admin:admin`.

You should try creating a new user and accessing the proxied mock services with the created user's credentials.

### Konga
Konga is a GUI for Kong's admin API. You probably don't need this but if you're curious to see how Kong was configured, visit `localhost:1337`, then create a new connection (name: <anything>: kong admin url: `http://kong:8001`).
