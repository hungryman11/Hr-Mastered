Feature: Loan compliance workflow — end-to-end business requirements
  As a company using the loan compliance module
  All loan case decisions must be governed by company boundaries and role permissions.

  Background:
    Given a company "Loan Co" exists
    And an HR Admin "loan_hr" belongs to "Loan Co"
    And a Risk Checker "loan_checker" belongs to "Loan Co"
    And a Compliance Admin "loan_admin" belongs to "Loan Co"
    And an Employee applicant "loan_applicant" belongs to "Loan Co"
    And a Loan Product "Quick Advance" with one required checklist item "Bank statement" exists for "Loan Co"

  # ── Loan product management ──────────────────────────────────────────────────

  Scenario: HR Admin creates a loan product for the company
    When the HR Admin posts a valid loan product creation request with name "Staff Advance"
    Then the product is stored under "Loan Co"
    And the product is returned in the loan-products list for company members

  Scenario: Loan product list is scoped to the requesting user's company
    Given a second company "Other Loan Co" with its own product exists
    When a member of "Loan Co" lists loan products
    Then only products belonging to "Loan Co" are returned

  # ── Loan case creation and checklist snapshot ────────────────────────────────

  Scenario: Creating a loan case snapshots the product checklist
    When the HR Admin creates a loan case for "loan_applicant" with product "Quick Advance"
    Then the case is created in IN_REVIEW status
    And the case has exactly one checklist item named "Bank statement"
    And a LoanAuditEvent with action "case_created" is recorded

  Scenario: Loan case creation requires a positive requested amount
    When the HR Admin creates a loan case with requested_amount of 0
    Then the request is rejected with a validation error

  Scenario: Loan case creation requires the applicant to belong to the same company
    Given a foreign employee "foreign_app" from "Other Loan Co" exists
    When the HR Admin creates a loan case with "foreign_app" as the applicant
    Then the request is rejected with a company boundary error

  # ── Risk checker evidence verification ──────────────────────────────────────

  Scenario: Risk Checker marks a checklist item as RECEIVED with evidence reference
    Given the loan case is in IN_REVIEW status
    When the Risk Checker verifies the "Bank statement" item with status RECEIVED and evidence_reference "BS-2026-001"
    Then the checklist item status is updated to RECEIVED
    And a LoanAuditEvent with action "checklist_verified" is recorded

  Scenario: Risk Checker must provide a note for MISSING or REJECTED status
    When the Risk Checker marks the item as MISSING with an empty note
    Then the request is rejected with a validation error on the note field

  Scenario: Risk Checker must provide an evidence reference for RECEIVED status
    When the Risk Checker marks the item as RECEIVED with an empty evidence_reference
    Then the request is rejected with a validation error on the evidence_reference field

  Scenario: An invalid checklist status is rejected
    When the Risk Checker submits status "UNKNOWN"
    Then the request is rejected with an invalid status error

  Scenario: A Risk Checker from a different company cannot verify evidence
    Given a Risk Checker "foreign_checker" from "Other Loan Co" exists
    When "foreign_checker" attempts to verify a checklist item for "Loan Co"
    Then the request is rejected

  # ── Compliance Admin decision ────────────────────────────────────────────────

  Scenario: Compliance Admin approves a case where all required evidence is received
    Given all required checklist items have status RECEIVED
    When the Compliance Admin submits decision APPROVED with reason "All checks passed"
    Then the case status changes to APPROVED
    And a LoanAuditEvent with action "case_decided" is recorded

  Scenario: Missing required evidence blocks an APPROVED decision
    Given the "Bank statement" checklist item is still in PENDING status
    When the Compliance Admin submits decision APPROVED with any reason
    Then the request is rejected with an incomplete evidence error

  Scenario: Compliance Admin can RETURN a case for further information
    When the Compliance Admin submits decision RETURNED with reason "More collateral documentation needed"
    Then the case status changes to RETURNED
    And the decision reason is persisted

  Scenario: Compliance Admin can REJECT a case
    When the Compliance Admin submits decision REJECTED with reason "Applicant does not meet criteria"
    Then the case status changes to REJECTED
    And the decision reason is persisted

  Scenario: Compliance Admin can request MORE_INFO
    When the Compliance Admin submits decision MORE_INFO with reason "Credit score report is required"
    Then the case status changes to MORE_INFO

  Scenario: A decision requires a non-empty reason
    When the Compliance Admin submits any decision with an empty reason
    Then the request is rejected with a validation error on the reason field

  Scenario: A Compliance Admin from a different company cannot decide a case
    Given a Compliance Admin "foreign_comp_admin" from "Other Loan Co" exists
    When "foreign_comp_admin" attempts to decide the loan case
    Then the request is rejected with a company boundary error

  Scenario: An invalid decision value is rejected
    When the Compliance Admin submits an unrecognised decision value "MAYBE"
    Then the request is rejected with an invalid decision error
