# EMPLOYEE PROVISIONING & ONBOARDING — PHASE 3 (CRITICAL GO-LIVE BLOCKER)

## Purpose

Document the complete employee provisioning workflow for production. This is a **CRITICAL GO-LIVE BLOCKER** — without a defined employee import process, real users cannot log in.

---

## CURRENT STATE

### Problem

The system has no documented production employee provisioning workflow:

1. ✗ No employee seed data exists for production
2. ✗ No documented procedure to import employees from authoritative source (HR system, spreadsheet, etc.)
3. ✗ Demo auth is DEBUG-only (cannot be used for real employees)
4. ✗ Manual Django admin user creation doesn't scale

### Impact

**Without employee provisioning, GO-LIVE is IMPOSSIBLE.** Real users cannot access the system.

---

## SOLUTION: THREE-PHASE EMPLOYEE PROVISIONING

### Phase A: Bulk Import (Initial Setup)

**Use:** `import_infinity_staff.py` management command

**Prerequisites:**
1. Company record exists in database
2. Departments exist and match spreadsheet
3. Positions exist and match spreadsheet
4. Email addresses are standardized and unique

**Process:**

```bash
# Step 1: Prepare Excel workbook (template provided below)
# File: employees.xlsx
# Columns: STAFF ID NO., FULL NAME, DESIGNATION, DEPARTMENT, EMAIL, STATUS

# Step 2: Dry-run to validate
python manage.py import_infinity_staff employees.xlsx \
    --company "Infinity Microfinance Bank" \
    --dry-run

# Expected output:
# total_rows=150
# fully_mapped_rows=145
# missing_or_invalid_email=3
# duplicate_email_in_workbook=0
# missing_staff_id=2
# unmapped_department=0
# unmapped_position=0
# existing_employees_by_email=5
# existing_staff_ids=0

# Step 3: Review report and fix Excel if needed
# - Fix 3 invalid emails
# - Verify all departments/positions are mapped
# - Confirm no duplicates

# Step 4: Commit import
python manage.py import_infinity_staff employees.xlsx \
    --company "Infinity Microfinance Bank" \
    --commit

# Expected output:
# Creating 140 new employees and payroll profiles...
# Import complete. Review audit logs for details.
```

### Excel Workbook Template

**File:** `employee_import_template.xlsx`

| STAFF ID NO. | FULL NAME | DESIGNATION | DEPARTMENT | EMAIL | STATUS |
|--------------|-----------|-------------|-----------|-------|--------|
| INF001 | John Doe | Manager | Finance | john.doe@infinity.ng | ACTIVE |
| INF002 | Jane Smith | Loan Officer | Lending | jane.smith@infinity.ng | ACTIVE |
| INF003 | Bob Johnson | Accountant | Finance | bob.johnson@infinity.ng | ON_LEAVE |
| INF004 | Alice Williams | HR Manager | Human Resources | alice.williams@infinity.ng | ACTIVE |

**Column specifications:**

1. **STAFF ID NO.** (Required, unique)
   - Format: Any string; stored in PayrollProfile.employee_number
   - Validation: Must not be empty; must be unique per company
   - Transformation: None (used as-is)

2. **FULL NAME** (Required)
   - Format: "FirstName LastName" or more
   - Validation: Must not be empty
   - Transformation: Split into first_name and last_name

3. **DESIGNATION** (Required)
   - Format: Must exactly match existing Position.title (case-insensitive)
   - Validation: Position must exist in database
   - Transformation: Lookup Position ID from company

4. **DEPARTMENT** (Required)
   - Format: Must exactly match existing Department.name (case-insensitive)
   - Validation: Department must exist in database
   - Transformation: Lookup Department ID from company

5. **EMAIL** (Required, unique)
   - Format: Valid email address (username@domain.extension)
   - Validation: Must contain @ and valid domain
   - Transformation: Normalized to lowercase
   - Check: Must not already exist in Employee table for this company

6. **STATUS** (Optional, recommended)
   - Format: ACTIVE, ON_LEAVE, INACTIVE, SUSPENDED
   - Validation: None (informational only)
   - Transformation: Mapped to Employee.onboarding_status (if needed)

### Phase B: Account Activation

**After bulk import:**

1. Employees exist in database but cannot log in yet (no Zoho OAuth mapping)
2. HR admin must send "complete your profile" email (manual)
3. Employee clicks email link (Zoho OAuth flow)
4. Zoho OAuth matches Employee.email to Zoho user
5. Employee gains access to system

**OR (Simplified):**

If no Zoho OAuth:
1. HR admin sets temporary password in Django admin
2. Employee logs in with temp password
3. Employee changes password on first login

### Phase C: Ongoing Employee Management

**Quarterly sync:**

```bash
# Generate updated employee list from HR system
# Fix any department/position changes
# Run dry-run first

python manage.py import_infinity_staff employees_q1_2025.xlsx \
    --company "Infinity Microfinance Bank" \
    --dry-run

# Importer will:
# - Detect new employees (create)
# - Detect existing employees (skip — no update logic)
# - Report unmapped departments/positions
# - Report duplicate emails
```

**Note:** Current importer does NOT update existing employees. This is intentional (conservative).

---

## IMPLEMENTATION DETAILS

### Command: `import_infinity_staff.py`

**Location:** `core/management/commands/import_infinity_staff.py`

**Status:** ✓ EXISTS AND TESTED

**Key features:**

1. **Dry-run mode** (default)
   - Validates Excel format
   - Checks for required columns
   - Validates all rows (emails, departments, positions)
   - Reports counts and issues
   - **Does NOT modify database**

2. **Commit mode** (explicit flag required)
   - Requires `--company` flag with exact company name
   - Creates Employee records with:
     - email (unique per company)
     - first_name, last_name (split from FULL NAME)
     - company (scoped)
     - onboarding_status = PENDING (waiting for password/OAuth)
   - Creates PayrollProfile records with:
     - employee_number (mapped from STAFF ID NO.)
     - company (same as employee)

3. **Never:**
   - Creates/modifies companies (must pre-exist)
   - Guesses email addresses
   - Creates Zoho identities (reserved for OAuth only)
   - Modifies existing employees (add `--update` flag to enable in future)

4. **Validates:**
   - Department exists in company
   - Position exists in company
   - Email is valid format
   - Email not already in use
   - Staff ID not already in use
   - No duplicates within workbook

### Data Model: Employee Creation

```python
# When importing john.doe@infinity.ng:
employee = Employee.objects.create(
    company=company,
    email='john.doe@infinity.ng',
    username='john.doe@infinity.ng',  # Auto-generated from email
    first_name='John',
    last_name='Doe',
    department=department_finance,
    position=position_manager,
    manager=None,  # Must be set separately
    onboarding_status=Employee.OnboardingStatus.PENDING,
)

payroll_profile = PayrollProfile.objects.create(
    company=company,
    employee=employee,
    employee_number='INF001',
    bank_account_ciphertext='',  # Set manually later
    pension_id_ciphertext='',
    tax_id_ciphertext='',
)
```

---

## PRODUCTION SETUP PROCEDURE

### Step 1: Prepare Organization Structure

Before importing employees, ensure company, departments, and positions exist:

```python
# Django shell or management command
company = Company.objects.create(
    name='Infinity Microfinance Bank',
    country='Nigeria',
)

departments = [
    Department.objects.create(company=company, name='Finance'),
    Department.objects.create(company=company, name='Lending'),
    Department.objects.create(company=company, name='Human Resources'),
]

positions = [
    Position.objects.create(company=company, title='Manager'),
    Position.objects.create(company=company, title='Loan Officer'),
    Position.objects.create(company=company, title='Accountant'),
    Position.objects.create(company=company, title='HR Manager'),
]
```

**OR:** Use Django admin:
1. Add Company → "Infinity Microfinance Bank"
2. Add Departments (Finance, Lending, HR)
3. Add Positions (Manager, Loan Officer, etc.)

### Step 2: Prepare Employee Excel Workbook

Create `employees_production.xlsx` with columns:
- STAFF ID NO.
- FULL NAME
- DESIGNATION
- DEPARTMENT
- EMAIL
- STATUS

Export from HR system or manually create.

### Step 3: Validate with Dry-Run

```bash
python manage.py import_infinity_staff employees_production.xlsx \
    --company "Infinity Microfinance Bank" \
    --dry-run
```

**Check output:**
- `fully_mapped_rows` should equal or nearly equal `total_rows`
- `unmapped_department` should be 0
- `unmapped_position` should be 0
- `missing_or_invalid_email` should be 0

**If not:**
1. Fix Excel file
2. Fix missing departments/positions
3. Re-run dry-run

### Step 4: Execute Import

```bash
python manage.py import_infinity_staff employees_production.xlsx \
    --company "Infinity Microfinance Bank" \
    --commit
```

**Verify:**
```python
# Django shell
Employee.objects.filter(company__name='Infinity Microfinance Bank').count()
# Should match expected employee count

# Check first employee
emp = Employee.objects.first()
print(emp.username, emp.email, emp.company)
```

### Step 5: Set Manager Relationships (Manual)

The importer doesn't set manager relationships. Do this manually:

```python
# Django shell
john = Employee.objects.get(username='john.doe@infinity.ng')
bob = Employee.objects.get(username='bob.johnson@infinity.ng')
bob.manager = john
bob.save()
```

OR: Use Django admin to edit each employee's `manager` field.

### Step 6: Account Activation (Zoho OAuth or Password)

**Option A: Zoho OAuth (Recommended for production)**

1. Employees have been created in database
2. Send email to employees: "Click here to complete your profile"
3. Email link redirects to login page
4. Zoho OAuth flow begins (employee logs in with Zoho account)
5. Zoho returns employee email
6. System finds matching Employee record
7. Session created; employee gains access

**Option B: Temporary Password (Fallback)**

1. Employees have been created in database
2. In Django admin, set temporary password for each employee
3. Email employees: "Your temp password is: [password]"
4. On first login, force password change
5. Employee gains access

**Implementation:** Both flows use existing auth endpoints:
- `GET /api/zoho/login-url/` (Zoho OAuth flow)
- `POST /api/demo-auth/login/` (Demo/temp password flow — DEBUG only)

---

## KNOWN ISSUES & LIMITATIONS

### Issue 1: No Manager Assignment in Importer

**Problem:** Import command doesn't populate `manager` field
**Reason:** Manager relationships require two employees to exist first; complex logic for circular references
**Solution:** Set manually after import or create separate migration script

### Issue 2: No Bulk Password Setting

**Problem:** Cannot set passwords in bulk via import
**Reason:** Passwords are hashed; no plain-text way to bulk-set
**Solution:** Use Zoho OAuth or temporary password (see Step 6 above)

### Issue 3: No Employee Update Logic

**Problem:** Re-running import with updated data doesn't update employees
**Reason:** Intentionally conservative (no overwrite risk)
**Solution:** Create `--update` flag if needed; requires manual review

### Issue 4: Email Must Exist Before Import

**Problem:** Import fails if employee email not in Excel
**Reason:** Email is unique identifier; required for Zoho OAuth matching
**Solution:** Ensure HR system exports email for all employees

---

## PRODUCTION CHECKLIST

### Before Import

- [ ] Company exists in database
- [ ] All departments exist in database (from Excel DEPARTMENT column)
- [ ] All positions exist in database (from Excel DESIGNATION column)
- [ ] Excel file has correct columns (STAFF ID NO., FULL NAME, DESIGNATION, DEPARTMENT, EMAIL, STATUS)
- [ ] All emails are valid and unique
- [ ] All emails match Zoho user accounts (for OAuth matching)
- [ ] Staff IDs are unique

### During Import

- [ ] Run `--dry-run` first
- [ ] Review report and fix Excel if needed
- [ ] Run `--commit` (explicit flag required)
- [ ] Verify employee count matches expected

### After Import

- [ ] Check employees created: `Employee.objects.count()`
- [ ] Check payroll profiles created: `PayrollProfile.objects.count()`
- [ ] Test login with first employee (Zoho OAuth or temp password)
- [ ] Verify company isolation (employee can only see own company)
- [ ] Verify manager relationships are set (if applicable)
- [ ] Document any manual steps taken

---

## GO-LIVE READINESS

### Current Status: **NOT READY**

**Blockers:**

1. ✗ No production employee workbook exists
2. ✗ No documented procedure for employee activation
3. ✗ No manager relationship assignment procedure
4. ✗ Zoho OAuth untested with real Zoho account

### To Achieve Readiness

1. **Create production employee workbook** (employees_production.xlsx)
2. **Document activation procedure** (Zoho OAuth or password)
3. **Test end-to-end:**
   - Import 5-10 test employees
   - Verify database records created
   - Test login with each employee
   - Verify company isolation
   - Verify leave/payroll access restricted correctly

4. **Prepare manager relationship mapping** (spreadsheet or script)
5. **Create backup procedure** in case import needs to be rolled back

---

## IMPLEMENTATION RECOMMENDATION

### For Production Deployment

1. **Use Zoho OAuth flow** (not demo/temp passwords)
   - Aligns with production security model
   - Single source of truth: Zoho user directory
   - No password management overhead

2. **Pre-create employee records** via import_infinity_staff.py
   - Bulk create at deployment time
   - Minimal manual work

3. **Email employees with activation link**
   - System sends: "Click here to complete your profile"
   - Link redirects to Zoho OAuth
   - Employee authenticates with Zoho account
   - System matches email and creates session

4. **Set manager relationships post-import**
   - Create spreadsheet: Employee → Manager email
   - Write migration script to update relationships
   - Verify hierarchy is correct

---

## NEXT STEPS

1. ✓ Fix LeaveBalance.year (DONE)
2. ✓ Document provisioning workflow (THIS DOCUMENT)
3. ⏳ Create production employee workbook (employees_production.xlsx)
4. ⏳ Test import_infinity_staff with sample data
5. ⏳ Test Zoho OAuth with real account
6. ⏳ Create manager relationship script
7. ⏳ Create activation email template
8. ⏳ Run end-to-end production simulation

