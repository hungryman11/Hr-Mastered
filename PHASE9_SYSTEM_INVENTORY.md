# Phase 9 System Inventory

## Backend

`core` provides company-scoped models for Company, Department, OrgUnit, Position, Employee, leave balances/requests/approval steps/decisions/documents, KPI templates/frameworks/items/overrides/assignments/measurements, performance cycles/reviews, salary records, payroll and delivery jobs. `core/api` exposes DRF viewsets under `/api/`; serializers enforce same-company relationships; services own leave routing, working-day calculation, KPI resolution/scoring, payroll and document delivery. Historical migrations end at `core.0044`; `makemigrations --check` reports no pending migration.

### Functional inventory

| Area | Implemented behavior |
|---|---|
| Employee and organisation | Company departments, hierarchical OrgUnits, positions and managers. Employee serializer/model validates an org-unit-bound position matches employee OrgUnit. |
| Leave | Self-service request, working-day calculation, dynamic OrgUnit/policy Head → HR route, immutable decisions, amendment/cancel, document generation and pending approval queue. |
| KPI | Categories, templates, scoped frameworks (GLOBAL/DEPARTMENT/POSITION), framework items, individual overrides, cycle assignment generation, measurements and scoring. |
| Performance | Cycle reviews and strict DRAFT → SUBMITTED → MANAGER_REVIEWED → HR_REVIEWED → CALIBRATED → FINALIZED actions. |
| Salary | Effective-dated component records, current salary endpoint, HR company ledger and supersede workflow. |
| Payroll/finance | Profiles/import validation, payroll runs/actions, statutory rules, deductions and disputes. |
| Administration | Employee onboarding, OrgUnit/position/leave configuration, holiday/work calendar and delivery job retry. |
| Authentication | Session authentication with Zoho OAuth callback/login endpoints. |
| Authorization and tenancy | Querysets/permissions scope users to company; roles are EMPLOYEE, SUPERVISOR, MANAGER, HOD, HR_ADMIN, FINANCE, ADMIN. Superuser/org-admin grants remain distinct. |
| Audit/history | Base timestamps/actors, immutable ApprovalDecision, approval steps/timeline, effective-dated salary history, finalized-review immutability and delivery records. |
| Zoho/documents/notifications | Zoho OAuth, WorkDrive document upload/folders, Zoho mail services and queued delivery jobs are implemented. Operational credentials/services were not live-tested. |

## Frontend

React/Vite routes use shared Axios client with CSRF headers and session credentials. Pages cover OAuth/login, dashboard, leave form/detail/queue, KPI templates/frameworks/assignments/cycles, performance review workflow, current salary/HR salary records, payroll/deductions and HR admin. Navigation is role-aware UX only; API authorization stays server-side.
