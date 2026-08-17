Feature: Payroll lifecycle — end-to-end business requirements
  As a company operating an HR platform
  All payroll workflow steps must be governed by company boundaries and role permissions.

  Background:
    Given a company "Payroll Co" exists
    And an HR Admin "hr_gherkin" belongs to "Payroll Co"
    And a Finance user "fin_gherkin" belongs to "Payroll Co"
    And an Employee "emp_gherkin" with a payroll profile belongs to "Payroll Co"
    And a payroll run for June 2026 is in DRAFT status

  # ── Payroll profile ─────────────────────────────────────────────────────────

  Scenario: HR Admin creates a payroll profile for an active employee
    Given the employee "emp_gherkin" does not yet have a payroll profile
    When the HR Admin posts a valid payroll profile creation request
    Then the profile is stored under "Payroll Co"
    And the base salary is persisted as a positive decimal
    And bank details are encrypted at rest

  Scenario: Payroll profile creation requires a positive base salary
    When the HR Admin posts a payroll profile with base_salary of 0
    Then the request is rejected with a validation error
    And no profile is saved

  # ── Payroll run calculation ──────────────────────────────────────────────────

  Scenario: HR Admin calculates payroll for all active employees
    Given the company has one active payroll profile
    When the HR Admin triggers the calculate action on the draft run
    Then the run status changes to CALCULATED
    And one PayrollItem is created per active profile
    And a PayrollAuditEvent with action "payroll_calculated" is recorded

  Scenario: Deductions are capped at the configured maximum percentage
    Given the maximum deduction percent is set to 25
    And an approved adjustment of 90000 exists for the employee
    When the HR Admin calculates the payroll run
    Then the total deductions for that employee do not exceed 25% of gross pay

  Scenario: HR Admin cannot calculate an already-calculated run
    Given the payroll run is in CALCULATED status
    When the HR Admin triggers the calculate action again
    Then the request is rejected with an appropriate error

  # ── Finance review and approval ──────────────────────────────────────────────

  Scenario: Finance reviews a calculated payroll run
    Given the payroll run is in CALCULATED status
    When the Finance user triggers the review action
    Then the run status changes to REVIEWED
    And a PayrollAuditEvent with action "payroll_reviewed" is recorded

  Scenario: Finance approves a reviewed payroll run
    Given the payroll run is in REVIEWED status
    When the Finance user triggers the approve action
    Then the run status changes to APPROVED
    And the approved_by field is set to the Finance user

  Scenario: The payroll maker cannot review their own run
    Given the payroll run was calculated by "hr_gherkin"
    When "hr_gherkin" attempts to review the run
    Then the request is rejected with a self-approval error

  # ── Settlement export ────────────────────────────────────────────────────────

  Scenario: Finance exports an approved payroll run as a settlement pack
    Given the payroll run is in APPROVED status
    When the Finance user exports the run in PACK format
    Then CSV, XLSX, and PDF files are created on the filesystem
    And a SettlementExport record is created for each format
    And the run status changes to EXPORTED
    And each export file has a SHA-256 checksum stored

  Scenario: An unapproved run cannot be exported
    Given the payroll run is in REVIEWED status
    When the Finance user triggers an export
    Then the request is rejected

  # ── Bank reconciliation ──────────────────────────────────────────────────────

  Scenario: Finance reconciles a successful bank settlement
    Given the payroll run is in EXPORTED status
    When the Finance user submits a reconciliation with result SUCCESS and bank reference "INF-001"
    Then the run status changes to RECONCILED
    And a ReconciliationRecord is created with the provided bank reference

  Scenario: Finance records a failed settlement
    Given the payroll run is in EXPORTED status
    When the Finance user submits a reconciliation with result FAILED
    Then the run status changes to FAILED
    And a ReconciliationRecord captures the failure details

  Scenario: A cross-company Finance user cannot reconcile a run
    Given a Finance user from a different company exists
    When that user attempts to reconcile the exported run
    Then the request is rejected with a company boundary error

  # ── Deduction disputes ───────────────────────────────────────────────────────

  Scenario: An employee contests their own deduction
    Given the payroll run is in CALCULATED status
    And the employee has a deduction for "Late arrival"
    When the employee submits a contest with a non-empty reason
    Then the deduction is_held flag is set to True
    And a PayrollAuditEvent with action "deduction_contested" is recorded

  Scenario: A contest requires a non-empty reason
    When the employee submits a contest with an empty reason
    Then the request is rejected with a validation error on the reason field

  Scenario: An employee cannot contest another employee's deduction
    Given a second employee "other_emp_gherkin" belongs to "Payroll Co"
    When "other_emp_gherkin" attempts to contest "emp_gherkin"'s deduction
    Then the request is rejected

  Scenario: Finance upholds a contested deduction
    Given the deduction is in a contested (is_held) state
    When the Finance user resolves with uphold=True and valid notes
    Then the deduction amount remains unchanged
    And the deduction is_held flag is cleared
    And a PayrollAuditEvent with action "deduction_resolved" is recorded

  Scenario: Finance removes a contested deduction
    Given the deduction is in a contested (is_held) state
    When the Finance user resolves with uphold=False and valid notes
    Then the deduction amount is set to zero
    And the employee net pay increases accordingly

  Scenario: Finance cannot resolve a deduction without resolution notes
    When the Finance user resolves with empty notes
    Then the request is rejected with a validation error on the notes field
