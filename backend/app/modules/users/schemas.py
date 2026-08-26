import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None
    role: str = "employee"  # "admin", "sub_admin", "employee", "client"
    status: str = "active"
    client_id: uuid.UUID | None = None
    assigned_client_ids: list[uuid.UUID] = []


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    password: str | None = None
    role: str | None = None
    status: str | None = None
    client_id: uuid.UUID | None = None
    is_active: bool | None = None
    assigned_client_ids: list[uuid.UUID] | None = None


class ResetPasswordRequest(BaseModel):
    new_password: str


class AssignedClientInfo(BaseModel):
    id: uuid.UUID
    company_name: str

    model_config = {"from_attributes": True}


class AssignedEmployeeInfo(BaseModel):
    id: uuid.UUID
    name: str
    email: str

    model_config = {"from_attributes": True}


class UserDetailResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    phone: str | None = None
    role: str
    status: str = "active"
    client_id: uuid.UUID | None = None
    managed_by: uuid.UUID | None = None
    is_active: bool
    created_at: datetime
    assigned_clients: list[AssignedClientInfo] = []

    model_config = {"from_attributes": True}


class EmployeePerformance(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    phone: str | None = None
    status: str = "active"
    is_active: bool = True
    assigned_clients: list[AssignedClientInfo] = []
    total_uploads: int = 0
    today_uploads: int = 0
    total_applications: int = 0
    today_applications: int = 0
    daily_target: int = 0
    completion_percentage: float = 0.0

    model_config = {"from_attributes": True}


class SubAdminCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None
    client_ids: list[uuid.UUID] = []
    employee_ids: list[uuid.UUID] = []


class SubAdminUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    password: str | None = None
    is_active: bool | None = None
    status: str | None = None
    client_ids: list[uuid.UUID] | None = None
    employee_ids: list[uuid.UUID] | None = None


class SubAdminResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    phone: str | None = None
    role: str = "sub_admin"
    status: str = "active"
    is_active: bool
    created_at: datetime
    assigned_clients_count: int = 0
    assigned_employees_count: int = 0
    assigned_clients: list[AssignedClientInfo] = []
    assigned_employees: list[AssignedEmployeeInfo] = []

    model_config = {"from_attributes": True}


class SubAdminAssignmentRequest(BaseModel):
    client_ids: list[uuid.UUID] = []
    employee_ids: list[uuid.UUID] = []


class SubAdminAssignmentDetails(BaseModel):
    sub_admin_id: uuid.UUID
    assigned_client_ids: list[uuid.UUID] = []
    assigned_employee_ids: list[uuid.UUID] = []
    available_clients: list[AssignedClientInfo] = []
    available_employees: list[AssignedEmployeeInfo] = []
