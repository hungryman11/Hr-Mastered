# Phase 9.1 UAT Data Strategy

Use a dedicated Infinity UAT company/database or tenant. Never load this dataset into production.

## Minimum company dataset

**Company:** Infinity Microfinance Bank

| Category | Minimum dataset |
|---|---|
| Org Units | Customer Service, Operations, Information Technology (three departments) |
| Users | One HR Administrator, one HOD, one Manager, two Employees and one Finance user; each with unique UAT credentials and company association |
| Positions | At least one position in each department; every org-unit-bound position must match its employee OrgUnit |
| Leave | Annual Leave, Sick Leave and one other configured leave type; opening balances for both employees |
| KPIs | Customer Acquisition (target 100, HIGHER), Loan Recovery Rate (target 90%, HIGHER), Complaint Resolution Time (target 24 hours, LOWER); include numeric, percentage and target-based templates |
| Frameworks | One GLOBAL, one DEPARTMENT and one POSITION framework, with weights totaling 100% |
| Performance | One active UAT cycle with generated assignments and one review taken through the complete controlled workflow |
| Salary | At least two employees with an ACTIVE salary record; supersede one to create history |

## Data controls

- Use synthetic names, email addresses and salary values.
- Keep Company A/Company B isolation records for security tests; do not cross-link employees, positions, frameworks or salaries.
- Keep a UAT data owner and reset only the dedicated UAT tenant/database between cycles.
- HR/business must decide KPI treatment for zero targets and negative measurements before using them in production policy.
