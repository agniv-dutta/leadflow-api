from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from models import LeadStatus


class LeadBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    company: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=1, max_length=50)
    source: str = Field(min_length=1, max_length=100)
    status: LeadStatus

    @field_validator("name", "company", "phone", "source")
    @classmethod
    def strip_and_validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned


class LeadCreate(LeadBase):
    pass


class LeadStatusUpdate(BaseModel):
    status: LeadStatus


class LeadRead(LeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class LeadListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[LeadRead]


class LeadActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    previous_status: LeadStatus
    new_status: LeadStatus
    changed_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)

    @field_validator("full_name")
    @classmethod
    def strip_optional_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None = None
    is_active: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
