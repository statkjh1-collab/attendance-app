# 브라이튼독출근부 — 출퇴근/월급 관리

관리자 한 명이 직원들의 출퇴근을 입력하면 시급 × 근무시간으로 월급이 자동 계산되는 웹앱입니다.
급여는 DB에 저장하지 않고, 출퇴근 기록으로부터 뷰(view)를 통해 항상 즉시 계산됩니다.

스택: Vue 3 (Vite) + FastAPI + Supabase, 배포는 Render.

## 프로젝트 구조

```
backend/    FastAPI 서버 (employees, attendance, payroll API)
frontend/   Vue 3 관리자 화면 (직원 / 출퇴근 / 급여 탭)
supabase_schema.sql   Supabase 테이블/뷰 정의 (SQL Editor에서 실행)
```

## 1. Supabase 준비

1. [supabase.com](https://supabase.com) 에서 프로젝트를 생성합니다.
2. 프로젝트 대시보드 → **SQL Editor** → New query 에 [supabase_schema.sql](supabase_schema.sql) 내용을 붙여넣고 실행합니다.
   - `employees`, `attendance` 테이블과 `attendance_pay`, `monthly_summary` 뷰가 생성됩니다.
   - 이미 두 테이블이 있는 프로젝트에서도 안전하게 재실행할 수 있도록 작성되어 있습니다(기존 데이터 보존, 뷰만 재생성, 누락 컬럼/제약만 추가).
3. 프로젝트 대시보드 → **Project Settings → API** 에서 아래 두 값을 복사해 둡니다.
   - `Project URL`
   - `service_role` 키 (⚠️ `anon` 키가 아닙니다. `eyJ...`로 시작하는 긴 JWT 문자열이며, 서버에서만 사용하고 절대 프론트엔드나 공개 저장소에 넣지 마세요.)

## 2. 백엔드 로컬 실행

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows(Git Bash). PowerShell은 .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env             # SUPABASE_URL, SUPABASE_SERVICE_KEY 채우기
uvicorn main:app --reload --port 8000
```

`http://localhost:8000/docs` 에서 API를 확인할 수 있습니다.

> **Windows 로컬 개발 참고:** 일부 Windows 환경(백신/보안 프로그램이 TLS를 가로채는 경우)에서 `CERTIFICATE_VERIFY_FAILED` 오류가 날 수 있습니다. `requirements.txt`에 포함된 `pip-system-certs` 패키지가 설치되어 있으면 Windows 인증서 저장소를 자동으로 사용해 해결됩니다. Render(Linux) 배포 환경에서는 필요 없습니다.

## 3. 프론트엔드 로컬 실행

```bash
cd frontend
npm install
cp .env.example .env    # VITE_API_BASE=http://localhost:8000
npm run dev
```

`http://localhost:5173` 접속 후 직원 등록 → 출퇴근 입력 → 급여 확인 순서로 테스트합니다.

## 4. Render 배포

### 4-1. GitHub에 코드 푸시

이 저장소를 GitHub에 올린 뒤 Render와 연동합니다.

### 4-2. 백엔드 — Web Service

Render 대시보드 → New → Web Service → 이 GitHub 저장소 선택 후:

| 설정 | 값 |
|---|---|
| Root Directory | `backend` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Environment Variables | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` |

배포 완료 후 발급되는 URL(예: `https://attendance-app-backend.onrender.com`)을 기록해 둡니다.

### 4-3. 프론트엔드 — Static Site

Render 대시보드 → New → Static Site → 같은 저장소 선택 후:

| 설정 | 값 |
|---|---|
| Root Directory | `frontend` |
| Build Command | `npm install && npm run build` |
| Publish Directory | `dist` |
| Environment Variables | `VITE_API_BASE=https://<백엔드-Render-URL>` |

### 4-4. CORS

백엔드 `main.py`의 CORS 설정은 기본적으로 모든 origin을 허용합니다. 운영 환경에서 도메인을 제한하고 싶다면 `backend/main.py`의 `allow_origins`를 실제 프론트엔드 도메인으로 좁혀주세요.

## 급여 계산 방식

- `manual_minutes`(근무시간 직접 입력)가 있으면 그 값을 우선 사용합니다.
- 없으면 `check_in`/`check_out` 시각에서 `break_minutes`를 뺀 값을 사용합니다(퇴근 시각이 출근보다 빠르면 다음날로 간주해 야간 근무를 처리합니다).
- 급여 = 근무분 ÷ 60 × 시급(원 단위 반올림), `attendance_pay` 뷰에서 항상 즉시 계산되며 별도로 저장하지 않습니다.
- `monthly_summary` 뷰가 월별 근무일수/총시간/총급여를 집계합니다.
