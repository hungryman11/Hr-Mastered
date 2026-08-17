# Infinity HR UAT Script

Mark every test **Pass** or **Fail** and add an evidence reference in Comments.

| Test ID | Role | Action | Expected result | Pass / Fail | Comments |
|---|---|---|---|---|---|
| UAT-001 | Employee | Log in and open Dashboard | Dashboard loads with own leave/KPI/review information only. |  |  |
| UAT-002 | Employee | Submit Annual Leave | Valid request is created with calculated working days and pending department/OrgUnit stage. |  |  |
| UAT-003 | HOD/Manager | Open Approvals | Only requests currently assigned to this user are displayed. |  |  |
| UAT-004 | HOD/Manager | Approve a request | Request advances to HR approval stage and timeline records action. |  |  |
| UAT-005 | HR Admin | Approve stage-two leave | Request becomes approved and leave balance updates. |  |  |
| UAT-006 | HOD/Manager | Reject a leave without/with reason | No-reason rejection is blocked; reason is recorded when supplied. |  |  |
| UAT-007 | Employee | Open KPI assignments and submit authorized measurement | Own assignment is visible; measurement saves and score updates as configured. |  |  |
| UAT-008 | HR Admin | Create template/framework/item and generate cycle assignments | Scope and weights validate; assignments are generated. |  |  |
| UAT-009 | Employee → Manager → HR | Run one performance review lifecycle | Only valid next actor can progress DRAFT to FINALIZED; finalized review is read-only. |  |  |
| UAT-010 | Employee | Open My Salary | Only own current salary components are visible; no edit/history access. |  |  |
| UAT-011 | HR Admin | Create salary record | Search employee by name/department, select one record, enter components and save. |  |  |
| UAT-012 | HR Admin | Supersede salary record | Selected employee’s old active record closes; new active effective-dated record appears in history. |  |  |
| UAT-013 | Finance | Open payroll/profile/run screens | Existing finance screens and actions remain available. |  |  |
| UAT-014 | All roles | Attempt prohibited UI/API actions | User receives a useful denial; no unauthorized data/action succeeds. |  |  |

## Required negative/security checks

- Employee attempts another employee’s salary, KPI and review URL/API identifier.
- Manager/HOD attempts an unrelated employee and another approver’s leave request.
- HR Admin from Company A attempts Company B records by UUID and numeric ID.
- Finance attempts HR-only KPI/salary action.
- Attempt invalid review transitions and duplicate/already-terminal leave decisions.
