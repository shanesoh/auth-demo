from pydantic import BaseModel


class User(BaseModel):
    username: str
    name: str


class ProfileBio(BaseModel):
    name: str
    address: str
    company: str


class ProfileContactDetails(BaseModel):
    email: str
    phone_number: str


class ProfileTechnicalDetails(BaseModel):
    msisdn: str
    user_agent: str


class ProfileComments(BaseModel):
    bio_comments: str
    general_comments: str


class Profile(BaseModel):
    profile_id: int
    owner: User
    bio: ProfileBio
    contact_details: ProfileContactDetails
    technical_details: ProfileTechnicalDetails
    comments: ProfileComments
