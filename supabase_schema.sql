-- ============================================================
-- 출퇴근/월급 관리 앱 - Supabase 스키마
-- Supabase 프로젝트의 SQL Editor 에서 그대로 실행하세요.
-- 이미 employees/attendance 테이블이 있는 프로젝트에도 안전하게
-- 재실행할 수 있도록 작성되어 있습니다(기존 데이터 보존, 뷰만 재생성).
-- ============================================================

create extension if not exists pgcrypto;

-- 1. 직원 테이블
create table if not exists employees (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  hourly_wage   integer not null check (hourly_wage >= 0),
  phone         text,
  memo          text,
  is_active     boolean not null default true,
  created_at    timestamptz not null default now()
);

alter table employees add column if not exists updated_at timestamptz not null default now();

-- 2. 출퇴근 기록 테이블
-- manual_minutes 가 있으면 그 값을 근무시간으로 우선 사용.
-- 없으면 check_in/check_out (+break_minutes) 으로 계산.
-- 야간 근무(퇴근 < 출근)는 check_out 이 다음날로 저장되어 있다고 가정(백엔드에서 보정해서 저장).
create table if not exists attendance (
  id              uuid primary key default gen_random_uuid(),
  employee_id     uuid not null references employees(id) on delete cascade,
  work_date       date not null,
  check_in        timestamptz,
  check_out       timestamptz,
  break_minutes   integer not null default 0 check (break_minutes >= 0),
  manual_minutes  integer check (manual_minutes >= 0),
  memo            text,
  created_at      timestamptz not null default now()
);

alter table attendance add column if not exists updated_at timestamptz not null default now();

create index if not exists idx_attendance_employee_date on attendance(employee_id, work_date);

-- 관리자가 직원별로 하루에 한 건만 입력하도록 유니크 제약 (upsert 기준)
do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'attendance_employee_id_work_date_key'
  ) then
    alter table attendance
      add constraint attendance_employee_id_work_date_key unique (employee_id, work_date);
  end if;
end $$;

-- updated_at 자동 갱신 트리거
create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_employees_updated_at on employees;
create trigger trg_employees_updated_at
  before update on employees
  for each row execute function set_updated_at();

drop trigger if exists trg_attendance_updated_at on attendance;
create trigger trg_attendance_updated_at
  before update on attendance
  for each row execute function set_updated_at();

-- ============================================================
-- 3. 급여 계산 뷰 (attendance_pay)
--    worked_minutes: manual_minutes 우선, 없으면 check_in/out - break 로 계산
--    pay: worked_minutes / 60 * hourly_wage (원 단위 반올림)
-- ============================================================
drop view if exists monthly_summary;
drop view if exists attendance_pay;

create view attendance_pay as
select
  a.id,
  a.employee_id,
  e.name as employee_name,
  e.hourly_wage,
  a.work_date,
  a.check_in,
  a.check_out,
  a.break_minutes,
  a.manual_minutes,
  a.memo,
  case
    when a.manual_minutes is not null then a.manual_minutes
    when a.check_in is not null and a.check_out is not null then
      greatest(
        0,
        (extract(epoch from (a.check_out - a.check_in)) / 60)::integer - a.break_minutes
      )
    else 0
  end as worked_minutes,
  round(
    (
      case
        when a.manual_minutes is not null then a.manual_minutes
        when a.check_in is not null and a.check_out is not null then
          greatest(
            0,
            (extract(epoch from (a.check_out - a.check_in)) / 60)::integer - a.break_minutes
          )
        else 0
      end
    )::numeric / 60 * e.hourly_wage
  )::integer as pay,
  a.created_at,
  a.updated_at
from attendance a
join employees e on e.id = a.employee_id;

-- ============================================================
-- 4. 월별 집계 뷰 (monthly_summary)
--    직원별 해당 월의 근무일수 / 총근무분 / 총근무시간 / 월급
-- ============================================================
create view monthly_summary as
select
  ap.employee_id,
  ap.employee_name,
  ap.hourly_wage,
  to_char(ap.work_date, 'YYYY-MM') as month,
  count(*) as work_days,
  sum(ap.worked_minutes) as total_minutes,
  round(sum(ap.worked_minutes) / 60.0, 2) as total_hours,
  sum(ap.pay) as total_pay
from attendance_pay ap
group by ap.employee_id, ap.employee_name, ap.hourly_wage, to_char(ap.work_date, 'YYYY-MM');

-- ============================================================
-- 참고: RLS(Row Level Security)는 이 앱에서는 백엔드(서비스 키)만 접근하므로 비활성 상태로 둡니다.
-- 필요 시 아래처럼 활성화하고 정책을 추가하세요.
-- alter table employees enable row level security;
-- alter table attendance enable row level security;
-- ============================================================
