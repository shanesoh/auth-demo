from faker import Faker
from fastapi import FastAPI, Header, Path, Query, HTTPException, Depends, Request
import os
import random
import requests
import schemas
import time
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


async def check_opa_authz(request: Request, x_access_token: str = Header(None), authorization: str = Header(None)):
    if authorization:
        token = authorization.split(' ')[1]
    elif x_access_token:
        token = x_access_token
    else:
        raise HTTPException(status_code=403, detail="No access token.")

    try:
        data = {
            "input": {
                "method": request.method,
                "path": request.url.path.split('/')[1:],
                "token": token
            }
        }
        resp = requests.post(opa_url + policy_path, json=data)
    except Exception as err:
        logging.error(err)
        raise HTTPException(status_code=500, detail=err)

    if resp.json()["result"].get("allow", False) is not True:
        logging.error("OPA denied access")
        raise HTTPException(status_code=401, detail="Forbidden!")
    else:
        return resp


@app.get("/whoami")
def whoami(resp=Depends(check_opa_authz)):
    """Gives you your username as long as you're not "admin"
    """
    return f"Hello {resp.json()['result']['token']['payload']['preferred_username']}"


@app.get("/profile/{profile_id}")
def get_profiles(profile_id: int = Path(..., example=1)):
    """Retrieve a profile.
    """
    profile = profiles_db.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@app.post("/lookupSsn")
def lookup_ssn(ssn: int = Query(..., example=12345), resp=Depends(check_opa_authz)):
    """Lookup in c3n for additional data attributed to a ssn

    This API relies on an external API call to c3n. The user's access token is passed to k2o via kong, k2o then uses
    that access token to call c3n (also via kong).

    NOTE: Currently c3n does not check for access token so passing it would seem redundant
    """
    token = resp.json()['result']['token']['raw']
    r = requests.post(f"https://c3n.kong.localhost/queryAddress?ssn={ssn}",
                      headers={"Authorization": f"Bearer {token}"},
                      verify=False)
    return r.json()
