from faker import Faker
from fastapi import FastAPI, Header, HTTPException
import os
import requests
import time
import jwt
import logging

app = FastAPI(
    title="k2o",
    docs_url="/"
)

faker = Faker()
profiles = [faker.profile() for _ in range(10)]
public_key = []


@app.on_event("startup")
def retrieve_public_key():
    """Retrieve public key from auth server (i.e. Keycloak) needed to validate JWT.
    """
    while public_key == []:
        try:
            r = requests.get(os.environ.get("ISSUER_ENDPOINT"), verify=False, timeout=60)
            if r.status_code == 200:
                public_key.append("-----BEGIN PUBLIC KEY-----\n" + r.json()["public_key"] + "\n-----END PUBLIC KEY-----")
            logging.info(f"Obtained public key: {public_key}")
        except:
            # This happens when this service starts together with Keycloak and the Keycloak's endpoints are not ready
            logging.info("Keycloak issuer endpoint not accessible. Trying again...")
            time.sleep(5)


@app.get("/profiles")
def get_profiles():
    """Get all profiles.

    This is a simple "hello world" endpoint that does not rely on external API calls.
    """
    return profiles


@app.post("/lookupSsn")
def lookup_ssn(ssn: int, x_access_token: str = Header(None)):
    """Lookup in c3n for additional data attributed to a ssn

    This API relies on an external API call to c3n. The user's access token is passed to k2o via kong, k2o then uses
    that access token to call c3n (also via kong).
    """
    logging.info(f"X-Access-Token: {x_access_token}")

    if public_key == []:
        raise HTTPException(status_code=401, detail="Missing public key")

    if not x_access_token:
        raise HTTPException(status_code=403, detail="No access token. Try accessing via Kong at k2o.kong.localhost.")

    claims = jwt.decode(x_access_token, public_key[0])
    logging.info(f"Decoded JWT: {claims}")
    # TODO: Check scope before posting
    r = requests.post(f"https://c3n.kong.localhost/queryAddress?ssn={ssn}",
                      headers={"Authorization": f"Bearer {x_access_token}"},
                      verify=False)
    return r.json()
