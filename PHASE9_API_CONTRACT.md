# Phase 9 API Contract Audit

All frontend API modules use the shared `/api/` Axios base client. No active `/api/core/...` client call was found.

| Frontend area | Verified route family |
|---|---|
| Auth | `/employees/me/`, Zoho auth routes |
| Leave | `/leave-balances/`, `/leave-requests/`, `routing/`, `pending-approvals/`, `approve/`, `reject/`, `cancel/` |
| KPI | `/kpi-templates/`, `/kpi-frameworks/`, `/performance-cycles/`, `/kpi-assignments/` |
| Performance | `/performance-reviews/` and documented actions |
| Salary | `/salary-records/`, `current/`, `supersede/` |
| Payroll | profiles, runs, adjustments, statutory rules and deductions |

All inspected API calls use trailing slashes. Request bodies match the current serializers/actions: leave creation is multipart, leave rejection sends `reason`, performance actions send decimal string score/comment fields, and salary supersede sends `employee_uuid` plus effective-dated components. Lists with backend pagination are unwrapped where the client implements it; KPI/leave/salary list consumers assume unpaginated DRF lists, matching current server defaults.

**UAT limitation:** salary-create UI accepts the backend numeric employee ID, which is contract-correct but should be replaced with an authorized employee selector before broad HR rollout.
