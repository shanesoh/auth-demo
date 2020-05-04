from faker import Faker
from fastapi import FastAPI, Header, HTTPException
import os
import random
import requests
import schemas
import time
import jwt
import logging

app = FastAPI(
    title="k2o",
    docs_url="/"
)


users_db = []
profiles_db = {}

@app.on_event("startup")
def bootstrap_mock_data():
    faker = Faker()

    # Create mock users
    for i in range(5):
        user = schemas.User(username=f"user{i}",
                            name=faker.name())
        users_db.append(user)

    # Create mock profiles
    for i in range(10):
        profile = schemas.Profile(profile_id=i,
                                  owner=random.choice(users_db),
                                  bio=schemas.ProfileBio(name=faker.name(),
                                                         address=faker.address(),
                                                         company=faker.company()),
                                  contact_details=schemas.ProfileContactDetails(email=faker.email(),
                                                                                phone_number=faker.phone_number()),
                                  technical_details=schemas.ProfileTechnicalDetails(msisdn=faker.msisdn(),
                                                                                    user_agent=faker.user_agent()),
                                  comments=schemas.ProfileComments(bio_comments=faker.paragraph(),
                                                                   general_comments=faker.paragraph())
                                  )
        profiles_db[i] = profile

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


@app.get("/whoami")
def whoami(x_access_token: str = Header(None),
           authorization: str = Header(None)):
    if authorization:
        token = authorization.split(' ')[1]
    else:
        token = x_access_token
    claims = jwt.decode(token, public_key[0], audience="account")
    logging.info(f"Decoded JWT: {claims}")

    return f"Hello {claims.get('preferred_username')}"


@app.get("/profile/{profile_id}")
def get_profiles(profile_id: int, x_access_token: str = Header(None),
                 authorization: str = Header(None)):
    """Retrieve a profile.

    Depending on your privileges, you may only see part of a profile.
    """
    if authorization:
        token = authorization.split(' ')[1]
    else:
        token = x_access_token
    logging.info(token)
    claims = jwt.decode(token, public_key[0], audience="account")
    logging.info(f"Decoded JWT: {claims}")

    profile = profiles_db.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@app.post("/lookupSsn")
def lookup_ssn(ssn: int, x_access_token: str = Header(None),
               authorization: str = Header(None)):
    """Lookup in c3n for additional data attributed to a ssn

    This API relies on an external API call to c3n. The user's access token is passed to k2o via kong, k2o then uses
    that access token to call c3n (also via kong).
    """
    if authorization:
        token = authorization.split(' ')[1]
    elif x_access_token:
        token = x_access_token
    else:
        raise HTTPException(status_code=403, detail="No access token. Try accessing via Kong at k2o.kong.localhost.")

    if public_key == []:
        raise HTTPException(status_code=401, detail="Missing public key")

    claims = jwt.decode(token, public_key[0])
    logging.info(f"Decoded JWT: {claims}")
    # TODO: Check scope before posting
    r = requests.post(f"https://c3n.kong.localhost/queryAddress?ssn={ssn}",
                      headers={"Authorization": f"Bearer {token}"},
                      verify=False)
    return r.json()
