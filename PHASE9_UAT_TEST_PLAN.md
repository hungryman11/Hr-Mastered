# Infinity HR UAT Test Plan

- [ ] **001 Employee login:** Sign in with Zoho session. Expected: dashboard and employee navigation load without salary of another employee.
- [ ] **002 Employee setup:** HR creates employee with company, OrgUnit, manager and position. Expected: a position bound to a different OrgUnit is rejected.
- [ ] **003 Leave request:** Employee submits valid leave. Expected: working days/balance/status are correct and request appears in My Leave.
- [ ] **004 Department approval:** Sign in as configured OrgUnit Head. Expected: request alone appears in Pending Approvals; approve moves it to HR.
- [ ] **005 Leave rejection:** Reject a request without a reason. Expected: rejection blocked; with reason, status/timeline record rejection.
- [ ] **006 HR leave approval:** HR approves a department-approved request. Expected: final approval, balance deduction and document/notification queue entry.
- [ ] **007 KPI configuration:** HR creates GLOBAL, DEPARTMENT and POSITION frameworks. Expected: invalid scope combinations are rejected.
- [ ] **008 KPI measurement:** Employee opens own assignment and submits a measurement. Expected: only authorized assignment can be changed; score reflects configured direction/weight.
- [ ] **009 Performance workflow:** Employee self-assesses; manager reviews; HR reviews, calibrates and finalizes. Expected: each action appears only at correct state; finalized review is read-only.
- [ ] **010 Salary security:** Employee opens Current Salary. Expected: only own ACTIVE record; peer UUID/ID access rejected. HR creates and supersedes a record; expected history preserved.
- [ ] **011 Tenant isolation:** Repeat employee, leave, KPI, review and salary attempts with Company A and B IDs/UUIDs. Expected: all cross-company reads/writes/actions rejected or absent.
- [ ] **012 Payroll:** Finance runs existing payroll/profile/deduction flow. Expected: existing finance pages remain usable.
