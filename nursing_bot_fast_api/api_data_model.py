from enum import Enum
from typing import Optional, Any, List
from pydantic import BaseModel, Field
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    username: str
    role: str  # "nurse" or "admin"
    access_token: str
    token_type: str


class RegisterNurseRequest(BaseModel):
    username: str
    password: str
    org_id: int 


class CreateOrganisationRequest(BaseModel):
    organisation_name: str
    system_prompt: str    


class EditOrganisationRequest(BaseModel):
    organisation_name: str
    system_prompt: Optional[str] = None
    faqs: Optional[Any] = None  # dict or list

class ResetPasswordRequest(BaseModel):
    username: str
    new_password: str
    organisation_name: str  # new field to identify the organisation


class PatientTreatmentItem(BaseModel):
    treatment_name: str
    dose: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


class PatientUpsertRequest(BaseModel):
    org_id: int
    patient_code: str
    first_name: str
    last_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    diagnosis: Optional[str] = None
    department: Optional[str] = None
    ward: Optional[str] = None
    bed_no: Optional[str] = None
    primary_doctor: Optional[str] = None
    status: Optional[str] = "admitted"
    summary: Optional[str] = None
    alias_names: Optional[str] = None
    treatments: Optional[List[PatientTreatmentItem]] = None
