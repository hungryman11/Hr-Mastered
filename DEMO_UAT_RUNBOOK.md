# Infinity Microfinance Bank UAT runbook

## Scope and safety

`seed_demo` creates data only for **Infinity Microfinance Bank — DEMO**. It does not alter production companies, Zoho configuration, OAuth identity data, or the supplied workbook. The local `/app/demo-login` page works only while Django `DEBUG=True`; it creates a normal Django session, so existing RBAC remains in force.

## Start and seed

From the project root:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver
```

In a second terminal:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173/app/demo-login` and choose one of the seeded accounts. All accounts use the local password `DemoPass123!`; the page logs in by selected demo username so a Zoho account is not required for UAT.

| Username | Role | UAT purpose |
| --- | --- | --- |
| `demo.hr.admin` | HR Admin | HR, KPI, performance and salary administration |
| `demo.manager` | Manager | Line-manager approvals and reviews |
| `demo.hod` | HOD | Operations hierarchy and approvals |
| `demo.employee` | Employee | Leave request, KPI assignment and salary view |
| `demo.employee2` | Employee | Second employee / reporting hierarchy |
| `demo.finance` | Finance | Finance and payroll views |
| `demo.supervisor` | Supervisor | Operations supervision |
| `demo.admin` | Admin | Administrative role coverage |

Run `seed_demo` again at any time to reconcile the known demo records. It is idempotent; it does not reset or delete unrelated data.

## Supervisor presentation flow

1. Log in as `demo.employee`; show the dashboard, current salary, KPI assignments, performance review and the pending annual-leave request.
2. Log in as `demo.manager`; open Approvals to show the request routed through the existing approval steps.
3. Log in as `demo.hr.admin`; show employee administration, KPI templates/framework, the `2026 UAT Performance Cycle`, performance review and salary records.
4. Log in as `demo.finance`; show the finance/payroll access boundary.
5. Log in as `demo.employee2`; demonstrate that employee-level access remains restricted to the person and their reporting line.

## Staff workbook reconciliation

Always inspect first. This command does not write data:

```powershell
.\.venv\Scripts\python.exe manage.py import_infinity_staff "C:\Users\HomePC\Downloads\data.xlsx" --dry-run --company "Infinity Microfinance Bank — DEMO"
```

The report maps `STAFF ID NO.` to `PayrollProfile.employee_number`, `EMAIL` to `Employee.email`, `DESIGNATION` to an existing `Position`, and `DEPARTMENT` to an existing `Department`. It does **not** invent emails, assign Zoho IDs, or map phone/gender/branch fields.

Only after all missing/invalid emails, duplicates, and unmapped departments/positions are reconciled can an operator explicitly apply a reviewed file:

```powershell
.\.venv\Scripts\python.exe manage.py import_infinity_staff "C:\path\to\reviewed.xlsx" --commit --company "Exact existing company name"
```

The supplied workbook is not part of the repository and must not be committed.

## Verification

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test core.tests -v 2
cd frontend
npm run build
```
