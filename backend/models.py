from datetime import date, time
from typing import Optional

from pydantic import BaseModel, Field


# ---------------- Employees ----------------

class EmployeeCreate(BaseModel):
    name: str
    hourly_wage: int = Field(ge=0)
    phone: Optional[str] = None
    memo: Optional[str] = None


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    hourly_wage: Optional[int] = Field(default=None, ge=0)
    phone: Optional[str] = None
    memo: Optional[str] = None
    is_active: Optional[bool] = None


# ---------------- Attendance ----------------

class AttendanceCreate(BaseModel):
    employee_id: str
    work_date: date
    manual_minutes: Optional[int] = Field(default=None, ge=0)
    check_in: Optional[time] = None
    check_out: Optional[time] = None
    break_minutes: int = Field(default=0, ge=0)
    memo: Optional[str] = None


class AttendanceUpdate(BaseModel):
    manual_minutes: Optional[int] = Field(default=None, ge=0)
    check_in: Optional[time] = None
    check_out: Optional[time] = None
    break_minutes: Optional[int] = Field(default=None, ge=0)
    memo: Optional[str] = None
    clear_manual_minutes: bool = False
    clear_check_times: bool = False
