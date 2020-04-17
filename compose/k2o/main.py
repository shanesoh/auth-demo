from faker import Faker
from fastapi import FastAPI, Header, HTTPException
import os
import requests
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
    r = requests.get(os.environ.get("ISSUER_ENDPOINT"), verify=False)
    if r.status_code == 200:
        public_key.append("-----BEGIN PUBLIC KEY-----\n" + r.json()["public_key"] + "\n-----END PUBLIC KEY-----")
    logging.info(f"Obtained public key: {public_key}")


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

    if public_key == []:
        raise HTTPException(status_code=401, detail="Missing public key")
    claims = jwt.decode(x_access_token, public_key[0])
    logging.info(f"Decoded JWT: {claims}")
    # TODO: Check scope before posting
    r = requests.post(f"https://c3n.kong.localhost/queryAddress?ssn={ssn}",
                      headers={"Authorization": f"Bearer {x_access_token}"},
                      verify=False)
    return r.json()
