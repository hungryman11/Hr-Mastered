# Final UAT Scenario for HR Platform Go/No-Go

## Objective
Validate that the production-ready RBAC and admin lifecycle flows work end-to-end for real users in both the happy path and the security boundary cases. The scenario below is designed to produce evidence for the final GO/NO-GO decision.

## Preconditions
- Production-like environment with seeded Company A and Company B data
- At least one superuser, one org admin, one HR admin, one manager, one employee per company
- Email and OAuth flows disabled or mocked to deterministic success/failure states
- Test data includes valid departments, org units, positions, and managers
- HR/Admin dashboard and employee management pages are accessible in the frontend

## Role-by-role UAT flow

### 1) Organization Admin
1. Log in as org admin for Company A.
2. Open the Admin Dashboard.
3. Confirm summary cards load with correct totals.
4. View employee list and verify they can see only Company A employees.
5. Create a new employee in Company A.
6. Assign department, org unit, position, manager, and role.
7. Save and confirm the record appears in the dashboard.
8. Patch an employee record to change manager or org unit.
9. Confirm org admin is allowed to do this only for Company A records.
10. Deactivate an employee and confirm the record remains in historical data but appears inactive.
11. Reactivate the same employee and verify status changes back to active.
12. Attempt to grant org admin to another employee via the set_org_admin endpoint.
13. Confirm it is rejected unless the user is a superuser.

Expected result: PASS if all actions succeed or reject exactly as required by policy.

### 2) HR Admin
1. Log in as HR admin for Company A.
2. Access the Admin Dashboard.
3. Verify they can see Company A employee summaries.
4. Create a new employee under Company A.
5. Attempt to set role/manager/org_unit on an existing employee.
6. Confirm the API rejects the change unless the user is an org admin/superuser.
7. Deactivate and reactivate an employee.
8. Confirm they can manage active/inactive status.
9. Attempt to list or open Company B employee detail.
10. Confirm access is denied or hidden.

Expected result: PASS if HR admin stays within company scope and cannot escalate org structure.

### 3) Manager
1. Log in as a manager in Company A.
2. View direct reports and allowed self data.
3. Confirm they cannot access the Admin Dashboard or HR admin APIs.
4. Attempt to patch their own role to HR_ADMIN or MANAGER.
5. Confirm the request is rejected.
6. Attempt to read another employee’s record outside their direct-report scope.
7. Confirm access is denied.

Expected result: PASS if manager is limited to self/report visibility and has no admin rights.

### 4) Employee
1. Log in as a normal employee.
2. Open /me/ and verify personal details render.
3. Attempt to patch their own role.
4. Confirm the patch is rejected.
5. Attempt to open another employee’s detail.
6. Confirm access is denied.
7. Attempt any cross-company access.
8. Confirm no data leakage occurs.

Expected result: PASS if the employee is limited to self-service and cannot view or modify others.

### 5) Cross-company isolation
1. Log in as HR admin from Company A.
2. Try to list departments, org units, positions, and employees for Company B.
3. Confirm no Company B records appear.
4. Attempt to read a Company B employee detail directly.
5. Confirm the response is 403 or 404.
6. Attempt to patch an employee with Company B department, org unit, manager, or position.
7. Confirm validation rejects it.

Expected result: PASS if no cross-company visibility or mutation is possible.

## Acceptance criteria
Evidence is sufficient for GO only if all of the following are true:
- All role-based UAT scenarios pass
- Cross-company isolation holds
- No mass assignment or privilege escalation works
- All required automated tests pass
- Security and admin lifecycle evidence is recorded in the release review

## Execution record template
- Date:
- Tester:
- Environment:
- Company A user:
- Company B user:
- Result:
- Observed issue(s):
- Sign-off:

## Status
This is the required UAT artifact for final GO/NO-GO signoff. It remains a required step until all scenarios above pass in an execution environment.
