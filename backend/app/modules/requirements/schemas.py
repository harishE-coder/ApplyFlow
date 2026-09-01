import uuid
from datetime import datetime

from pydantic import BaseModel, model_validator


class RequirementBase(BaseModel):
    client_id: uuid.UUID | None = None
    company: str  # e.g. "TCS", "Infosys", "Amazon"
    job_title: str | None = None  # e.g. "Java Developer"
    role: str | None = None       # e.g. "Java Developer" (alias)
    role_code: str | None = None  # e.g. "TCS-JAVA-01"
    job_url: str | None = None    # e.g. "https://careers.tcs.com/job/12345"
    priority: str = "Medium"      # "High", "Medium", "Low"
    notes: str | None = None
    status: str = "active"        # "active", "done", "archived"
    assignment_type: str = "all"  # "all" or "individual"
    assigned_employee_id: uuid.UUID | None = None
    assigned_employee: str | None = None  # "ALL" or string UUID


class RequirementCreate(RequirementBase):
    @model_validator(mode="after")
    def populate_titles(self):
        if not self.job_title and self.role:
            self.job_title = self.role
        elif not self.role and self.job_title:
            self.role = self.job_title
        elif not self.job_title and not self.role:
            self.job_title = "Open Role"
            self.role = "Open Role"

        if not self.role_code:
            prefix = "".join(c for c in self.company if c.isalnum())[:3].upper() or "JOB"
            role_part = "".join(c for c in (self.job_title or "ROLE") if c.isalnum())[:4].upper()
            self.role_code = f"{prefix}-{role_part}-01"

        if self.assigned_employee == "ALL" or not self.assigned_employee_id:
            self.assignment_type = "all"
            self.assigned_employee_id = None
        else:
            self.assignment_type = "individual"

        return self


class RequirementUpdate(BaseModel):
    company: str | None = None
    job_title: str | None = None
    role: str | None = None
    role_code: str | None = None
    job_url: str | None = None
    priority: str | None = None
    notes: str | None = None
    status: str | None = None
    assignment_type: str | None = None
    assigned_employee_id: uuid.UUID | None = None
    assigned_employee: str | None = None


class RequirementResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    client_name: str
    company: str
    job_title: str
    role: str
    role_code: str
    job_url: str | None = None
    priority: str = "Medium"
    notes: str | None = None
    status: str = "active"
    assignment_type: str = "all"
    assigned_employee_id: uuid.UUID | None = None
    assigned_employee_name: str | None = None
    created_by: uuid.UUID | None = None
    creator_name: str | None = None
    completed_by: uuid.UUID | None = None
    completer_name: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    total_resumes: int = 0
    total_applications: int = 0

    model_config = {"from_attributes": True}


class RequirementShort(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    company: str
    job_title: str | None = None
    role: str
    role_code: str
    job_url: str | None = None
    priority: str = "Medium"
    status: str
    assignment_type: str = "all"
    assigned_employee_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}
