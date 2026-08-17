# Hr‑Mastered

**Hr‑Mastered** is a multi-tenant, company-scoped HR, payroll, performance management, and compliance platform built with Django 5.x REST Framework and a React + Vite SPA.

---

## 🌟 Key Features

- **Employee Lifecycle & Organogram**: Complete management of employee roles (`HR_ADMIN`, `FINANCE`, `MANAGER`, `HOD`, `EMPLOYEE`), positions, hierarchical organizational units (`OrgUnit`), and superuser-governed organogram administration.
- **Leave Management & 2-Stage Approvals**: Two-tier approval routing (`Stage 1: Department Head` $\rightarrow$ `Stage 2: HR Admin`), delegation authority with tenant boundary guards, concurrency row locking, and immutable audit trails.
- **KPI Framework & Inheritance Engine**: Dynamic multi-level KPI inheritance (`GLOBAL` $\rightarrow$ `DEPARTMENT` $\rightarrow$ `POSITION`), framework items with weighted targets, and employee-level overrides (`ADD`, `MODIFY`, `REMOVE`).
- **Mathematical KPI Scoring Engine**: Directional normalization (`HIGHER_IS_BETTER`, `LOWER_IS_BETTER`, `TARGET_BASED`, `BOOLEAN`, `RATING`), boundary score clamping ($[\text{min\_score}, \text{max\_score}]$), and weighted contribution calculations.
- **Performance Review & Calibration**: 6-stage review state machine (`DRAFT` $\rightarrow$ `SUBMITTED` $\rightarrow$ `MANAGER_REVIEWED` $\rightarrow$ `HR_REVIEWED` $\rightarrow$ `CALIBRATED` $\rightarrow$ `FINALIZED`), HR calibration curves, and strict immutability enforcement on finalized records.
- **Salary History & Component-Based Compensation**: Granular salary structure (base salary, housing, transport, meal, and other allowances), effective-date history tracking, overlap prevention validation, and atomic supersede workflow.
- **Payroll Pipeline**: Automated calculation, maximum deduction capping, maker-checker approval workflows, multi-format settlement exports (CSV, XLSX, PDF), bank reconciliation tracking, and deduction contest resolution.
- **Zoho WorkDrive & Mail Integration**: Background worker daemon (`run_delivery_worker`) ensuring idempotent file delivery, lease locking, exponential backoff, and retry handling.
- **Security & Data Isolation**: Company-scoped multi-tenancy enforced at model and view layers, AES-256 field encryption for sensitive payload data, and comprehensive audit trail recording.

---

## 🧪 Testing & Quality Assurance

### Local Setup & Verification

```bash
# 1. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 2. Run Django system check
python manage.py check

# 3. Run full test suite (136 tests)
python manage.py test core --verbosity=2
```

---

## 🚀 Deployment & Operations

### Production Architecture (Render.com)

- **Web Service**: Gunicorn-backed Django API & static asset host.
- **Worker Service**: Long-running background worker executing `python manage.py run_delivery_worker`.
- **Database**: Managed PostgreSQL instance.

For detailed Render deployment steps, environment variables, and migration instructions, see [`docs/PRODUCTION_SETUP.md`](file:///c:/Users/HomePC/Downloads/Hr-Mastered-updated/Hr-Mastered-main/docs/PRODUCTION_SETUP.md).
