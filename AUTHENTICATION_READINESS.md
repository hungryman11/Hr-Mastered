# Authentication Readiness Audit

## Authentication model

The platform uses Django sessions and DRF session authentication, not token-only authentication. This is appropriate for a same-domain web application with a React SPA served from the same origin.

Key settings:

- `rest_framework.authentication.SessionAuthentication`
- `DEFAULT_PERMISSION_CLASSES = ['rest_framework.permissions.IsAuthenticated']`
- explicit login backed by Django `login(request, user)`

## Demo/UAT auth isolation

The demo auth endpoints in `core/api/demo_auth.py` are intentionally limited to `DEBUG=True` and are isolated to a debug company dataset. They are not part of the live production authentication path.

This separation is correct and important:

- demo users remain debug-only
- production user login is not routed through the demo path
- security posture remains unchanged
- no live employee authentication is hidden behind mock/demo flows

## CSRF protection

The project keeps CSRF enabled. The Axios client in `frontend/src/api/client.ts` checks whether an explicit `X-CSRFToken` header is already present before injecting a value. This is the correct production-safe pattern because it avoids overriding a caller-specified token while still setting it when absent.

## Zoho authentication

Zoho SSO is implemented with redirect-flow state validation and server-side token exchange. The code logs only sanitized values and keeps sensitive OAuth data out of logs.

Notable safeguards:

- state checking during callback flow
- redirect URI validation
- matching redirect URIs from explicit allow-list
- safe handling of OAuth errors in debug vs production mode

## RBAC and company scoping

The project enforces role-based access via `core/permissions.py`:

- `IsCompanyMember`
- `IsHRAdmin`
- `IsSuperUserOnly`
- `IsOrgAdmin`
- `IsFinanceOrHRAdmin`
- `IsManagerOrHRAdmin`
- `IsSelfOrManagerOrHRAdmin`
- `CanViewApprovalDecision`

These permission classes protect data access by company boundary and role, which is necessary for multi-tenant HR operations.

## Verdict

The authentication architecture is production-safe and correctly layered. The demo flow is isolated, CSRF remains enabled, and RBAC is enforced at the permission layer. The remaining requirement is environment-specific configuration, not a code-level weakening of security.
