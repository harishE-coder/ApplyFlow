import uuid
from datetime import datetime
from pydantic import BaseModel


class RequirementBase(BaseModel):
    client_id: uuid.UUID
    company: str  # e.g. "TCS", "Infosys", "Amazon"
    role: str     # e.g. "Java Developer", "Frontend Engineer"
    role_code: str # e.g. "TCS-JAVA-01"
    status: str = "active"


class RequirementCreate(RequirementBase):
    pass


class RequirementUpdate(BaseModel):
    company: str | None = None
    role: str | None = None
    role_code: str | None = None
    status: str | None = None


class RequirementResponse(RequirementBase):
    id: uuid.UUID
    client_name: str
    created_at: datetime
    total_resumes: int = 0
    total_applications: int = 0

    model_config = {"from_attributes": True}


class RequirementShort(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    company: str
    role: str
    role_code: str
    status: str

    model_config = {"from_attributes": True}
