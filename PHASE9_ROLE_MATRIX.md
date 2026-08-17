# Phase 9 Role Matrix

| Capability | Employee | Supervisor | Manager | HOD | HR Admin | Finance | Admin |
|---|---:|---:|---:|---:|---:|---:|---:|
| Own leave / balance | Read/create/cancel | Read/create | Read/create | Read/create | Company read/manage | Company member read | Company member read |
| Leave approval | Assigned step only | Assigned step only | Assigned step only | Assigned step only | Assigned HR step / company view | No dedicated authority | No dedicated authority |
| Employees | Self/read direct reports as scoped | Scoped | Direct reports | Backend org scope as implemented | Company CRUD | No HR CRUD | No HR authority inferred |
| KPI configuration | Read only | Read only | Read only | Read only | CRUD | Read only | Read only |
| KPI assignment/measurement | Own | Own | Self/direct reports | Current backend scope | Company | Own/read scope | Own/read scope |
| Performance | Self assessment | Own | Direct-report review | Department read scope | HR review/calibrate/finalize | Own/read scope | Own/read scope |
| Salary | Own ACTIVE/current only | Own ACTIVE/current only | Own ACTIVE/current only | Own ACTIVE/current only | Company history/create/supersede | No salary write | No salary authority inferred |
| Payroll | Deductions as scoped | As scoped | As scoped | As scoped | HR/finance scope | Finance workflow | No finance authority inferred |

Frontend navigation matches the major implemented roles but is not authorization. Two UAT checks remain: supervisor/admin navigation must be confirmed against intended business responsibilities, because their backend permissions are limited/general rather than dedicated HR role flows.
