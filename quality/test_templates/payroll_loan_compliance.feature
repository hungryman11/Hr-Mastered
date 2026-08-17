Feature: Payroll and loan compliance guardrails
  Scenario: Payroll profile creation requires a valid employee and positive salary
    Given a company HR administrator creates a payroll profile for an employee in the same company
    When the payload is valid
    Then the profile is stored with a payroll company scope

  Scenario: Loan case creation copies the configured checklist snapshot
    Given a loan product has a checklist template
    When a loan case is created for an applicant in the same company
    Then the case receives one checklist item per template entry

  Scenario: Missing evidence blocks compliance approval
    Given a risk checker records missing or rejected checklist evidence without a note
    When compliance admin attempts to approve the case
    Then the decision is rejected and the loan case audit is preserved
