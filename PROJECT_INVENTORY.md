# Project Inventory

## Product overview

Hr-Mastered is a Django 5.x + DRF + React/Vite multi-tenant HR platform for employee management, leave processing, payroll, KPI tracking, and document/workflow automation. The application is designed for a same-domain deployment model where the React frontend and Django backend are served from the same origin in production.

## Core backend

- `hr_platform/` — Django project configuration and routing.
- `core/` — primary application logic, models, permissions, API endpoints, onboarding logic, leave processing, payroll, KPI, and security checks.
- `zoho/` — Zoho OAuth, WorkDrive integration, and mail-related code.
- `templates/` — Django HTML templates used by the app shell and OAuth entry points.

## Frontend

- `frontend/` — Vite React application.
- `frontend/src/api/client.ts` — shared Axios client with CSRF-aware request handling.
- `frontend/src/pages/` — feature pages such as leave, payroll, HR admin, KPI, and demo login.

## Data and deployment artifacts

- `render.yaml` — Render deployment blueprint.
- `Dockerfile` — container build configuration.
- `build.sh` — build pipeline wiring for frontend + backend + static generation.
- `.env.template` — local environment template; production values must be injected via the hosting environment.
- `db.sqlite3` — local SQLite database used for development/testing by default.
- `manage.py` — Django management entry point.

## Warning on demo/UAT isolation

The repository includes a debug demo-auth path that is intentionally limited to `DEBUG=True` for local/UAT demo usage only. This flow must not be treated as a production login path. It must remain isolated and not share credentials or identity flows with the real Zoho / live employee authentication model.

## Key operational modules

- Authentication and authorization: `core/permissions.py`, `hr_platform/settings.py`, `zoho/views.py`
- Leave management: `core/onboarding.py`, `core/models/leave.py`, `core/leave_serializers.py`
- Payroll: `core/payroll.py`, `core/payroll_serializers.py`, `core/api/payroll_views.py`
- KPI: `core/kpi_service.py`, `core/kpi_scoring_service.py`, `core/api/kpi_views.py`
- Delivery / background jobs: `core/delivery.py`, `core/models/delivery.py`
- Security and encryption: `core/security.py`, `hr_platform/settings.py`

## Production deployment posture

Status: Ready for environment-specific deployment as long as the live environment sets the required secrets and disables demo-only paths in production.

Required production controls:

- `DEBUG=False`
- strong `SECRET_KEY`
- dedicated `FIELD_ENCRYPTION_KEY`
- PostgreSQL connection details in production
- valid `CSRF_TRUSTED_ORIGINS`
- valid Zoho credentials and redirect URIs
- production-safe SSL and cookie settings
- `ZOHO_USE_MOCK=False` in live deployment

## Verification baseline

The repository currently passes the required Django system check and the backend test suite for `core.tests` in the validated environment:

- `python manage.py check`
- `python manage.py test core.tests -v 2`
- `npm.cmd run build` (frontend)

The live codebase is not a mock-only application. The demo auth path is intentionally debug-scoped, while live production paths remain active and protected.
