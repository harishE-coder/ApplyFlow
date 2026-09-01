import uuid
from datetime import date

from pydantic import BaseModel


class TargetSetRequest(BaseModel):
    employee_id: uuid.UUID
    client_id: uuid.UUID
    daily_target: int
    status: str = "active"


class TargetResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: str
    client_id: uuid.UUID
    client_name: str
    daily_target: int
    status: str = "active"
    effective_date: date

    model_config = {"from_attributes": True}


class ClientTargetProgress(BaseModel):
    client_id: uuid.UUID
    client_name: str
    daily_target: int
    achieved_count: int
    completion_percentage: float


class EmployeeTargetProgressResponse(BaseModel):
    total_target: int
    total_achieved: int
    overall_percentage: float
    client_breakdown: list[ClientTargetProgress] = []
