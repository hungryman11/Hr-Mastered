# PROJECT LIVE AUDIT — Phase 0: System Inventory

## Executive Summary

Hr-Mastered is a Django 5.x + React/Vite + PostgreSQL HR platform with multi-tenant employee lifecycle, leave management, KPI tracking, and payroll functionality. The system integrates with Zoho OAuth, WorkDrive, and email services.

**Current Status: PARTIALLY IMPLEMENTED — Multiple production blockers identified**

---

## 1. DJANGO APPLICATIONS & MODELS

### 1.1 Core Application (`core/`)

Status: **WORKING (with caveats)**

**Models (all company-scoped except noted):**

| Model | Status | Purpose | Blocking Issues |
|-------|--------|---------|-----------------|
| Company | WORKING | Multi-tenant root entity | None |
| Employee | WORKING | User identity, roles, org hierarchy | Zoho OAuth mapping untested in production |
| Department | WORKING | Organizational grouping | None |
| Position | WORKING | Job titles, org unit linking | None |
| OrgUnit | WORKING | Hierarchical org structure | None |
| LeaveType | WORKING | Leave policies (annual, sick, etc.) | Max days validation missing for some types |
| LeaveBalance | WORKING | Leave entitlements by employee/type/year | Year field defaults to 2026 (HARDCODED) |
| LeaveRequest | WORKING | Leave approval workflow | WorkDrive upload failure handling (non-blocking by design) |
| LeaveApprovalStep | WORKING | Two-stage approval routing | None |
| ApprovalDecision | WORKING | Immutable audit trail of decisions | None |
| ApprovalDocument | WORKING | Generated leave documents | WorkDrive upload status tracked |
| LeaveApprovalPolicy | WORKING | Policy configuration for routing | None |
| CompanyHoliday | WORKING | Company-specific holiday dates | Nigerian public holidays hardcoded |
| CompanyWorkCalendar | WORKING | Work calendar configuration (weekdays, holidays) | None |
| KpiCategory | WORKING | KPI grouping | None |
| KpiTemplate | WORKING | KPI definition, measurement type, direction | None |
| KpiFramework | WORKING | KPI hierarchy assignment to orgs/positions | Framework weights must sum to 100 |
| KpiFrameworkItem | WORKING | Individual KPIs in a framework | None |
| EmployeeKpiAssignment | WORKING | Employee-specific KPI assignment snapshot | None |
| EmployeeKpiOverride | WORKING | Employee KPI add/modify/remove actions | None |
| KpiMeasurement | WORKING | KPI measurement value | None |
| PerformanceCycle | WORKING | Review period | None |
| PerformanceReview | WORKING | 6-stage review state machine | Frontend state display needs verification |
| PayrollProfile | WORKING | Employee payroll data | Bank/pension/tax fields AES-256 encrypted at rest |
| PayrollConfig | WORKING | Company payroll settings | Hardcoded defaults present |
| StatutoryRule | WORKING | Tax/pension rates | None |
| PayrollAdjustment | WORKING | Bonus, advance, deduction entries | None |
| PayrollRun | WORKING | Monthly payroll calculation | Unique by (company, month) |
| PayrollItem | WORKING | Line-item salary/deduction | None |
| PayrollDeduction | WORKING | Specific deduction types | None |
| SalaryRecord | WORKING | Salary component history | Overlap prevention validated |
| DeliveryJob | WORKING | Background job queue | Lease-locked with retry logic |
| WorkDriveFolder | WORKING (Zoho) | Employee WorkDrive folder registry | None |
| EmployeeDocument | WORKING (Zoho) | Document metadata | None |
| EmailLog | WORKING (Zoho) | Email send history | None |

**Key concerns with models:**

1. **LeaveBalance.year hardcoded to 2026** — This will break in 2027.
2. **No production employee seed data** — System requires explicit employee provisioning.
3. **Nigerian public holidays hardcoded** — No dynamic configuration for other locales.

---

### 1.2 Zoho Application (`zoho/`)

Status: **PARTIALLY WORKING — OAuth untested in production**

**Models:**

| Model | Status | Purpose | Notes |
|-------|--------|---------|-------|
| WorkDriveFolder | WORKING | Zoho folder registry | Mock and real modes supported |
| EmployeeDocument | WORKING | Document metadata | Zoho file IDs stored |
| EmailLog | WORKING | Email audit trail | Simple logging |

**Services:**

| Service | Status | Functionality | Blocking Issues |
|---------|--------|---------------|-----------------|
| ZohoWorkDriveService | WORKING | Token refresh, folder creation, file upload | Real Zoho credentials required; mock mode only for UAT |
| ZohoAuthService | UNTESTED | OAuth 2.0 flow, code exchange, user profile fetch | No live Zoho account tested against; STATE validation implemented |
| ZohoMailService | WORKING | Email send via Zoho SMTP | Requires valid Zoho email account |

---

## 2. API ENDPOINTS & VIEWSETS

Status: **MOSTLY WORKING — Authorization layer needs UAT**

### 2.1 Employee Management

**Endpoints:**

- `GET/POST /api/employees/` — EmployeeViewSet (IsCompanyMember permission)
- `GET /api/employees/me/` — Current user profile
- `GET/PATCH /api/employees/{id}/` — Detail view

**Status:** WORKING
**Tests:** Backend unit tests pass; integration tests pass
**Issue:** No frontend E2E test; no cross-company access test

### 2.2 Leave Management

**Endpoints:**

- `GET/POST /api/leave-requests/` — LeaveRequestViewSet
- `GET/PATCH /api/leave-requests/{uuid}/` — Request detail
- `PATCH /api/leave-requests/{uuid}/approve/` — Approval action
- `PATCH /api/leave-requests/{uuid}/reject/` — Rejection action
- `PATCH /api/leave-requests/{uuid}/cancel/` — Cancellation action
- `PATCH /api/leave-requests/{uuid}/amend/` — Amendment action
- `GET /api/approval-decisions/` — Immutable approval audit trail
- `GET /api/leave-types/` — Configured leave types
- `GET/PATCH /api/leave-balances/` — Employee leave entitlements
- `GET/POST /api/holidays/` — Company holidays
- `GET/PATCH /api/work-calendars/` — Work week configuration

**Status:** WORKING
**Tests:** 96 backend tests (all passing); state machine tests passing
**Issue:** No E2E browser test; no WorkDrive-unavailable scenario E2E test

### 2.3 KPI Management

**Endpoints:**

- `GET/POST /api/kpi-templates/` — Template definitions
- `GET/POST /api/kpi-categories/` — KPI grouping
- `GET/POST /api/kpi-frameworks/` — Framework hierarchy
- `GET/POST /api/kpi-framework-items/` — Individual KPIs in framework
- `GET/POST /api/kpi-measurements/` — KPI values
- `GET/POST /api/kpi-assignments/` — Employee KPI assignment
- `POST /api/performance-cycles/{uuid}/initialize_reviews/` — Bulk review initialization
- `GET/POST /api/performance-reviews/` — Review records

**Status:** WORKING
**Tests:** KPI scoring tests passing; inheritance tests passing
**Issue:** No production KPI template seed; no real measurement data

### 2.4 Payroll Management

**Endpoints:**

- `GET/POST /api/payroll-profiles/` — Employee payroll configuration
- `GET/POST /api/payroll-runs/` — Monthly payroll calculation
- `GET/POST /api/payroll-adjustments/` — Bonus/deduction entries
- `GET/POST /api/salary-records/` — Salary history
- `POST /api/salary-records/supersede/` — Salary change workflow
- `GET /api/salary-records/current/` — Current salary
- `GET /api/salary-records/ledger/` — Salary history

**Status:** WORKING
**Tests:** Payroll tests passing; overlap prevention validated
**Issue:** No production payroll profile seed; no real payroll calculation E2E test

### 2.5 Authentication & Authorization

**Endpoints:**

- `GET /api/zoho/login-url/` — Zoho OAuth URL generation
- `GET /api/zoho/auth/callback/` — Zoho OAuth callback handler
- `GET /api/demo-auth/users/` — Demo user list (DEBUG only)
- `POST /api/demo-auth/login/` — Demo session creation (DEBUG only)

**Status:** MOSTLY WORKING
**Tests:** Demo auth tests passing; authorization tests passing
**Issue:** Real Zoho OAuth untested in production

### 2.6 Document Management

**Endpoints:**

- `GET /api/approval-documents/` — Read-only document metadata

**Status:** WORKING (with dependency)
**Tests:** Document generation tested; WorkDrive upload failure handled
**Issue:** Document upload success depends on Zoho WorkDrive availability

---

## 3. MIGRATIONS & SCHEMA

Status: **WORKING**

**Total migrations:** 44 (core) + 2 (zoho) = 46
**Schema:** PostgreSQL
**Key constraints:**
- Company scoping enforced in many models
- Unique constraints on (company, name) for many entities
- Employee.zoho_user_id unique
- PayrollProfile unique on (company, employee_number)

**Status:** WORKING
**Issue:** Migrations reference year 2026 in LeaveBalance seed data

---

## 4. AUTHENTICATION & PERMISSIONS

Status: **MOSTLY WORKING — Needs production validation**

### 4.1 Authentication Methods

| Method | Status | Usage | Production Ready |
|--------|--------|-------|------------------|
| Django Session | WORKING | All authenticated API calls | YES |
| Zoho OAuth 2.0 | UNTESTED | Production employee login | **NO** — untested |
| Demo auth | WORKING | Debug/UAT only | DEBUG=True only |

### 4.2 Permission Classes

| Class | Status | Purpose | Tested |
|-------|--------|---------|--------|
| IsCompanyMember | WORKING | Authenticated + company scoped | YES (unit tests) |
| IsHRAdmin | WORKING | HR_ADMIN role only | YES (unit tests) |
| IsSuperUserOnly | WORKING | Superuser only | YES (unit tests) |
| IsOrgAdmin | WORKING | Organogram editing | YES (unit tests) |
| IsFinanceOrHRAdmin | WORKING | Payroll access | YES (unit tests) |
| IsManagerOrHRAdmin | WORKING | Manager/HR access | YES (unit tests) |
| IsSelfOrManagerOrHRAdmin | WORKING | Self, manager, or HR | YES (unit tests) |
| CanViewApprovalDecision | WORKING | Approval audit visibility | YES (unit tests) |

**Status:** WORKING at unit level
**Issue:** No E2E browser test verifying unauthorized cross-company access returns 403

---

## 5. EMPLOYEE PROVISIONING

Status: **NOT IMPLEMENTED FOR PRODUCTION**

### Current state:
- Demo seed script creates demo users (`seed_demo.py`)
- Staff import script exists (`import_infinity_staff.py`) — imports from XLSX
- No production provisioning documented
- No employee account lifecycle management

### Issue:
**PRODUCTION BLOCKER:** How do real employees get created?

- Manual Django admin? (not scalable)
- CSV import? (requires documented format)
- Zoho sync? (not implemented)
- HR portal self-service? (not implemented)

---

## 6. FRONTEND APPLICATION

Status: **WORKING (React 19 + Vite 5.4.21)**

### Routes

| Route | Component | Auth Required | Status |
|-------|-----------|---------------|--------|
| `/` | Login | NO | WORKING |
| `/app/callback` | OAuthCallback | NO | WORKING (with Zoho OAuth untested) |
| `/app/dashboard` | Dashboard | YES | WORKING |
| `/app/employees` | Employee list | YES | WORKING |
| `/app/employees/{id}` | Employee detail | YES | UNTESTED |
| `/app/leave-requests` | Leave list | YES | WORKING |
| `/app/leave-requests/create` | Leave form | YES | WORKING |
| `/app/leave-requests/{uuid}` | Leave detail | YES | WORKING |
| `/app/kpi-templates` | KPI template list | YES | WORKING |
| `/app/kpi-frameworks` | KPI framework list | YES | WORKING |
| `/app/performance-cycles` | Performance cycle list | YES | WORKING |
| `/app/performance-reviews` | Performance review list | YES | WORKING |
| `/app/salary-records` | Salary records | YES | WORKING |
| `/app/payroll-profiles` | Payroll profiles | YES (Finance) | WORKING |
| `/app/payroll` | Payroll admin | YES (Finance) | WORKING |

**Build status:** ✓ Vite production build succeeds (14.59s)
**Bundle size:** 316.49 kB JS / 17.49 kB CSS (gzipped: 98.07 kB / 4.14 kB)

---

## 7. EXTERNAL INTEGRATIONS

### 7.1 Zoho OAuth

Status: **IMPLEMENTED BUT UNTESTED IN PRODUCTION**

**Implementation:**
- `ZohoAuthService.get_authorization_url()` — generates login URL
- `ZohoAuthService.exchange_code_for_tokens()` — code → access token
- `ZohoAuthService.fetch_user_profile()` — get user email
- `ZohoAuthService.find_existing_employee()` — employee lookup by email
- OAuth state validation implemented
- Redirect URI validation implemented

**Tests:** None (all mock or skipped)
**Issues:** 
- No real Zoho account tested
- Token refresh untested
- Expired token handling untested
- Revoked access handling untested

### 7.2 Zoho WorkDrive

Status: **WORKING IN MOCK MODE; UNTESTED IN PRODUCTION**

**Implementation:**
- Folder creation
- File upload
- Retry logic with exponential backoff
- Mock mode supported

**Tests:** Mock mode only
**Issues:** 
- No production Zoho WorkDrive tested
- Upload failure fallback validated in unit tests (leave request still created)
- Network failure handling untested

### 7.3 Zoho Email (SMTP)

Status: **IMPLEMENTED BUT NOT TESTED IN PRODUCTION**

**Configuration:**
- `EMAIL_HOST=smtp.zoho.com`
- `EMAIL_PORT=587`
- `EMAIL_USE_TLS=True`

**Usage:**
- Leave notifications
- Approval notifications
- Payroll/payslip if implemented

**Tests:** Mocked in unit tests
**Issues:** No real Zoho email account tested; no delivery verification

---

## 8. BACKGROUND JOBS & DELIVERY

Status: **WORKING (with caveats)**

**DeliveryService (core/delivery.py):**
- Queues approval documents and emails
- `DeliveryJob` model with lease locking
- Exponential backoff (1, 2, 4 minutes; max 3 attempts)
- Idempotency via job tracking

**Worker:** `python manage.py run_delivery_worker`

**Status:** WORKING
**Tests:** Delivery tests passing
**Issue:** Worker must be running for documents/emails to deliver; Render blueprint includes worker, but no verification it stays running

---

## 9. CONFIGURATION & ENVIRONMENT

Status: **ENVIRONMENT-DEPENDENT**

### Required environment variables:

```
# Security
SECRET_KEY=<required for production>
DEBUG=False
FIELD_ENCRYPTION_KEY=<required for payroll>

# Database
DATABASE_URL=postgresql://user:pass@host/db

# Hosting
ALLOWED_HOSTS=<production domain>
CSRF_TRUSTED_ORIGINS=https://<production domain>
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True

# Zoho
ZOHO_CLIENT_ID=<required if not mock>
ZOHO_CLIENT_SECRET=<required if not mock>
ZOHO_REFRESH_TOKEN=<required if not mock>
ZOHO_ORG_ID=<required if not mock>
ZOHO_USE_MOCK=False
ZOHO_OAUTH_REDIRECT_URI=<production callback URL>
ZOHO_ALLOWED_REDIRECT_URIS=<comma-separated>

# Email
EMAIL_HOST=smtp.zoho.com
EMAIL_HOST_USER=<zoho email>
EMAIL_HOST_PASSWORD=<app password>
DEFAULT_FROM_EMAIL=<sender>

# Optional
MAX_LEAVE_WORKING_DAYS=15
DELIVERY_JOB_LEASE_SECONDS=300
```

**Status:** DOCUMENTED
**Issue:** No production guardrail — app starts even with missing secrets

---

## 10. TESTING COVERAGE

Status: **UNIT TESTED; E2E NOT TESTED**

### Backend tests (96 total)

| Category | Count | Status |
|----------|-------|--------|
| Demo/Seeding | 8 | PASS |
| Employee/Position/Org | 9 | PASS |
| KPI | 18 | PASS |
| Leave | 18 | PASS |
| Leave State Machine | 5 | PASS |
| Performance Review | 5 | PASS |
| Salary | 15 | PASS |
| Tenant Security | 6 | PASS |
| Contract/Phase 75 | 1 | PASS |

**All passing with mock Zoho.**

### Frontend tests

**Status:** NO E2E TESTS FOUND
**Vitest configured but likely not running E2E scenarios**

---

## 11. DEPLOYMENT CONFIGURATION

Status: **CONFIGURED FOR RENDER.COM**

**render.yaml defines:**

1. **Web Service:** Gunicorn on `$PORT`
   - Build: `./build.sh`
   - Start: `gunicorn hr_platform.wsgi:application --bind 0.0.0.0:$PORT`
   - Environment: DEBUG=False, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, SSL=True

2. **Worker Service:** Background delivery jobs
   - Build: `./build.sh`
   - Start: `python manage.py run_delivery_worker`

3. **Database:** PostgreSQL (managed)
   - Connection via DATABASE_URL

**Status:** WORKING
**Issue:** Render-specific; no other hosting tested

---

## 12. PRODUCTION READINESS ASSESSMENT

### WORKING (Ready for testing with caveats)

✓ Django system check passes  
✓ Backend test suite passes (96/96)  
✓ Frontend build succeeds  
✓ Database migrations complete  
✓ Multi-tenancy isolation enforced  
✓ Authorization layer implemented  
✓ CSRF protection enabled  
✓ Session auth configured  
✓ Delivery queue implemented  
✓ Document generation working  

### PARTIALLY WORKING (Needs production validation)

⚠ Zoho OAuth (implemented but untested with real Zoho)  
⚠ Zoho WorkDrive (working in mock; untested in production)  
⚠ Zoho Email (configured but untested)  
⚠ Employee provisioning (no documented production flow)  
⚠ Payroll calculation (implemented but no E2E test)  
⚠ KPI scoring (implemented but no real-data test)  

### NOT IMPLEMENTED / MISSING

✗ Production employee seed/import  
✗ Real Zoho OAuth testing  
✗ E2E browser tests  
✗ Production configuration guardrails  
✗ Operational runbook  
✗ Backup/recovery procedure  
✗ Monitoring/alerting  
✗ Health check endpoint  

---

## 13. KNOWN ISSUES & HARDCODED VALUES

1. **LeaveBalance.year defaults to 2026**
   - Location: `core/models/leave.py`
   - Risk: HIGH — will break in 2027
   - Fix: Use `timezone.now().year` or make configurable

2. **Nigerian public holidays hardcoded**
   - Location: `core/holidays.py`
   - Risk: LOW (can be configured per company)
   - Fix: Allow company-level holiday configuration

3. **No production employee provisioning documented**
   - Risk: CRITICAL — blocks real user login
   - Fix: Implement and document provisioning workflow

4. **No real Zoho OAuth testing**
   - Risk: CRITICAL — auth flow untested
   - Fix: Test with real Zoho account in staging

5. **No E2E browser tests**
   - Risk: HIGH — UI workflows untested
   - Fix: Implement Playwright/Cypress tests

6. **No health check endpoint**
   - Risk: MEDIUM — production monitoring blind
   - Fix: Implement GET /health with dependency checks

---

## PHASE 0 CONCLUSION

**Overall Status: PARTIALLY PRODUCTION-READY**

**Blockers for GO-LIVE:**

1. ✗ Employee provisioning workflow (CRITICAL)
2. ✗ Real Zoho OAuth testing (CRITICAL)
3. ✗ E2E browser testing (HIGH)
4. ✗ Production configuration guardrails (HIGH)
5. ✗ Health check endpoint (MEDIUM)

**Recommend: Proceed to PHASE 1-3 (Configuration, Database, Employee Provisioning) before testing live systems.**
