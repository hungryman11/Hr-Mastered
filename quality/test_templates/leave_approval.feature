Feature: Sequential leave approval
  Scenario: A request advances through the configured organogram
    Given an employee has an Admin, Supervisor, HOD, and HR approval route
    When the employee submits a valid leave request
    Then only the Admin stage is notified
    When every current-stage approver approves with a reason
    Then the next stage is notified
    And final approval occurs only after HR approves

  Scenario: A later approver cannot skip the current stage
    Given a submitted leave request awaiting Admin approval
    When HR attempts to approve it
    Then the decision is rejected with a forbidden response

  Scenario: A decision needs an explanation
    Given an approver is assigned to the current stage
    When they approve or reject with a blank reason
    Then the decision is rejected with a validation error

  Scenario: Sensitive records are tenant and role scoped
    Given a standard employee is authenticated
    When they request email logs or attempt to create a leave type
    Then the API denies access

  Scenario: Zoho login verifies the browser session
    Given a pre-provisioned active employee starts a Zoho login
    When Zoho returns a matching authorization code and state
    Then the employee receives an authenticated session
    And a callback without the saved state is rejected

  Scenario: Leave document delivery is mandatory
    Given an employee submits a leave request
    When there is no valid supporting document or WorkDrive is unavailable
    Then the request is rejected and no leave request is stored
