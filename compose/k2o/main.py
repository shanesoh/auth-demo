from faker import Faker
from fastapi import FastAPI, Header, HTTPException, Depends, Request
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

opa_url = os.environ.get("OPA_ADDR", "http://localhost:8181")
policy_path = os.environ.get("POLICY_PATH", "/v1/data/authz")

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
    while not public_key:
        try:
            r = requests.get(os.environ.get("ISSUER_ENDPOINT"), verify=False, timeout=60)
            if r.status_code == 200:
                public_key.append(
                    "-----BEGIN PUBLIC KEY-----\n" +
                    r.json()["public_key"] +
                    "\n-----END PUBLIC KEY-----")
            logging.info(f"Obtained public key: {public_key}")
        except BaseException:
            # This happens when this service starts together with Keycloak and the Keycloak's endpoints are not ready
            logging.info("Keycloak issuer endpoint not accessible. Trying again...")
            time.sleep(5)


async def verify_decode_token(x_access_token: str = Header(None), authorization: str = Header(None)):
    if authorization:
        token = authorization.split(' ')[1]
    elif x_access_token:
        token = x_access_token
    else:
        raise HTTPException(status_code=403, detail="No access token.")

    logging.info(f"Access Token: {token}")
    claims = jwt.decode(token, public_key[0], audience="kong-k2o")
    logging.info(f"Decoded JWT: {claims}")
    return {"raw": token, "claims": claims}


async def check_opa_authz(request: Request, x_access_token: str = Header(None), authorization: str = Header(None)):
    if authorization:
        token = authorization.split(' ')[1]
    elif x_access_token:
        token = x_access_token
    else:
        raise HTTPException(status_code=403, detail="No access token.")

    try:
        data = {"input":
                {"method": request.method,
                 "path": request.url.path.split('/')[1:],
                 "token": token}
                }
        r = requests.post(opa_url + policy_path, json=data)
    except Exception as err:
        logging.error(err)
        raise HTTPException(status_code=500, detail=err)

    if r.json()["result"].get("allow", False) is not True:
        logging.error("OPA denied access")
        raise HTTPException(status_code=401, detail="Forbidden!")


@app.get("/whoami", dependencies=[Depends(check_opa_authz)])
def whoami(token: dict = Depends(verify_decode_token)):
    return f"Hello {token['claims'].get('preferred_username')}"


@app.get("/profile/{profile_id}")
def get_profiles(profile_id: int, token: dict = Depends(verify_decode_token)):
    """Retrieve a profile.
    """
    profile = profiles_db.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@app.post("/lookupSsn")
def lookup_ssn(ssn: int, token: dict = Depends(verify_decode_token)):
    """Lookup in c3n for additional data attributed to a ssn

    This API relies on an external API call to c3n. The user's access token is passed to k2o via kong, k2o then uses
    that access token to call c3n (also via kong).
    """
    # TODO: Check scope before posting
    r = requests.post(f"https://c3n.kong.localhost/queryAddress?ssn={ssn}",
                      headers={"Authorization": f"Bearer {token['raw']}"},
                      verify=False)
    return r.json()
