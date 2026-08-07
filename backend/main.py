from datetime import date, datetime, timedelta
from calendar import monthrange
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from db import supabase
from models import AttendanceCreate, AttendanceUpdate, EmployeeCreate, EmployeeUpdate

app = FastAPI(title="출퇴근/월급 관리 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def month_bounds(month: str) -> tuple[date, date]:
    try:
        year, mon = (int(p) for p in month.split("-"))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="month은 YYYY-MM 형식이어야 합니다.")
    last_day = monthrange(year, mon)[1]
    return date(year, mon, 1), date(year, mon, last_day)


def combine_datetime(work_date: date, t, next_day: bool = False) -> str:
    d = work_date + timedelta(days=1) if next_day else work_date
    return datetime.combine(d, t).isoformat()


# ============================================================
# Employees
# ============================================================

@app.get("/employees")
def list_employees(is_active: Optional[bool] = Query(default=None)):
    q = supabase.table("employees").select("*").order("created_at", desc=False)
    if is_active is not None:
        q = q.eq("is_active", is_active)
    res = q.execute()
    return res.data


@app.post("/employees", status_code=201)
def create_employee(payload: EmployeeCreate):
    res = supabase.table("employees").insert(payload.model_dump()).execute()
    return res.data[0]


@app.put("/employees/{employee_id}")
def update_employee(employee_id: str, payload: EmployeeUpdate):
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="수정할 내용이 없습니다.")
    res = supabase.table("employees").update(data).eq("id", employee_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")
    return res.data[0]


@app.delete("/employees/{employee_id}")
def delete_employee(employee_id: str):
    res = (
        supabase.table("employees")
        .update({"is_active": False})
        .eq("id", employee_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")
    return {"ok": True}


# ============================================================
# Attendance
# ============================================================

@app.get("/attendance")
def list_attendance(
    employee_id: Optional[str] = Query(default=None),
    month: Optional[str] = Query(default=None),
    work_date: Optional[date] = Query(default=None),
):
    q = supabase.table("attendance_pay").select("*")
    if employee_id is not None:
        q = q.eq("employee_id", employee_id)
    if work_date is not None:
        q = q.eq("work_date", work_date.isoformat())
    elif month is not None:
        start, end = month_bounds(month)
        q = q.gte("work_date", start.isoformat()).lte("work_date", end.isoformat())
    q = q.order("work_date", desc=False)
    res = q.execute()
    return res.data


def _build_attendance_row(payload: AttendanceCreate) -> dict:
    row = {
        "employee_id": payload.employee_id,
        "work_date": payload.work_date.isoformat(),
        "break_minutes": payload.break_minutes,
        "memo": payload.memo,
        "manual_minutes": None,
        "check_in": None,
        "check_out": None,
    }
    if payload.manual_minutes is not None:
        row["manual_minutes"] = payload.manual_minutes
    elif payload.check_in is not None and payload.check_out is not None:
        next_day = payload.check_out < payload.check_in
        row["check_in"] = combine_datetime(payload.work_date, payload.check_in)
        row["check_out"] = combine_datetime(payload.work_date, payload.check_out, next_day=next_day)
    else:
        raise HTTPException(
            status_code=400,
            detail="manual_minutes 또는 check_in/check_out 중 하나는 필요합니다.",
        )
    return row


@app.post("/attendance", status_code=201)
def create_attendance(payload: AttendanceCreate):
    row = _build_attendance_row(payload)
    res = (
        supabase.table("attendance")
        .upsert(row, on_conflict="employee_id,work_date")
        .execute()
    )
    saved = res.data[0]
    pay_res = (
        supabase.table("attendance_pay").select("*").eq("id", saved["id"]).execute()
    )
    return pay_res.data[0]


@app.put("/attendance/{attendance_id}")
def update_attendance(attendance_id: str, payload: AttendanceUpdate):
    existing_res = supabase.table("attendance").select("*").eq("id", attendance_id).execute()
    if not existing_res.data:
        raise HTTPException(status_code=404, detail="기록을 찾을 수 없습니다.")
    existing = existing_res.data[0]
    work_date = date.fromisoformat(existing["work_date"])

    data: dict = {}
    if payload.break_minutes is not None:
        data["break_minutes"] = payload.break_minutes
    if payload.memo is not None:
        data["memo"] = payload.memo

    if payload.clear_manual_minutes:
        data["manual_minutes"] = None
    elif payload.manual_minutes is not None:
        data["manual_minutes"] = payload.manual_minutes
        data["check_in"] = None
        data["check_out"] = None

    if payload.clear_check_times:
        data["check_in"] = None
        data["check_out"] = None
    elif payload.check_in is not None and payload.check_out is not None:
        next_day = payload.check_out < payload.check_in
        data["check_in"] = combine_datetime(work_date, payload.check_in)
        data["check_out"] = combine_datetime(work_date, payload.check_out, next_day=next_day)
        data["manual_minutes"] = None

    if not data:
        raise HTTPException(status_code=400, detail="수정할 내용이 없습니다.")

    supabase.table("attendance").update(data).eq("id", attendance_id).execute()
    pay_res = (
        supabase.table("attendance_pay").select("*").eq("id", attendance_id).execute()
    )
    return pay_res.data[0]


@app.delete("/attendance/{attendance_id}")
def delete_attendance(attendance_id: str):
    res = supabase.table("attendance").delete().eq("id", attendance_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="기록을 찾을 수 없습니다.")
    return {"ok": True}


# ============================================================
# Payroll
# ============================================================

@app.get("/payroll")
def payroll(month: str = Query(...)):
    month_bounds(month)  # validate format
    res = (
        supabase.table("monthly_summary")
        .select("*")
        .eq("month", month)
        .order("employee_name", desc=False)
        .execute()
    )
    return res.data


@app.get("/")
def health():
    return {"status": "ok"}
