import re
from pydantic import BaseModel, field_validator


class RegisterRequest(BaseModel):
    full_name: str
    contact: str
    password: str
    address: str | None   = None
    latitude: str | None  = None
    longitude: str | None = None

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Full name is required.")
        return v

    @field_validator("contact")
    @classmethod
    def valid_contact(cls, v):
        v = v.strip()
        if not (re.match(r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$", v) or
                re.match(r"^[6-9]\d{9}$", v)):
            raise ValueError("Provide a valid email or 10-digit Indian mobile number.")
        return v

    @field_validator("password")
    @classmethod
    def password_length(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class LoginRequest(BaseModel):
    contact: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_name: str
    user_email: str | None
    user_phone: str | None
    user_location: str | None


class UserOut(BaseModel):
    id: int
    full_name: str
    email: str | None
    phone: str | None
    address: str | None
    latitude: str | None
    longitude: str | None
    alert_threshold: int

    model_config = {"from_attributes": True}