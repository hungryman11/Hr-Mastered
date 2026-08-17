# Phase 9.1 Release Gates

| Gate | Acceptance criterion | Status before UAT |
|---|---|---|
| 1 Authentication | Login/OAuth session works in Infinity UAT | Pending UAT environment |
| 2 Role permissions | Each role can perform only assigned actions | Automated checks passed; validate in UAT |
| 3 Tenant isolation | Cross-company access rejected | Automated checks passed |
| 4 Leave workflow | Employee → configured approver → HR → approved | Automated checks passed; UAT required |
| 5 KPI workflow | Configuration, assignment and measurement work | Automated checks passed; UAT required |
| 6 Performance workflow | Strict review transitions work | Automated checks passed; UAT required |
| 7 Salary workflow | Current-only employee access and HR history/supersede work | Automated checks passed; UAT required |
| 8 Frontend build | Production build succeeds | Passed |
| 9 Backend tests | Core suite succeeds | 88 passed |
| 10 Business acceptance | Infinity HR accepts workflows and usability | Pending |

Production cannot proceed with a P0, a P1 in a core HR workflow, failed tenant isolation, salary confidentiality failure, or authorization failure.
