# Production Configuration Audit

## Summary

The application is structured for a same-domain deployment pattern and is generally production-aware, but deployment correctness depends on environment variables being set correctly in the live hosting environment. The codebase does not contain a hardcoded production trust policy; instead it reads environment-based configuration from `settings.py` and the target environment.

## Confirmed configuration pattern

### Security and cookie configuration

`hr_platform/settings.py` correctly establishes the following production security posture:

- `DEBUG` is derived from environment and defaults to `False`.
- `SECRET_KEY` is required when `DEBUG` is off.
- `ALLOWED_HOSTS` is read from an environment list.
- `CSRF_TRUSTED_ORIGINS` is read from an environment list.
- `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` become enabled when `DEBUG` is off.
- `SECURE_SSL_REDIRECT` is environment-controlled.
- `SECURE_HSTS_*` settings are configured as production-safe defaults.

### Production deployment config

`render.yaml` is aligned with a production deployment model:

- web service with Gunicorn on `$PORT`
- background worker for delivery jobs
- Postgres database resource
- `DEBUG=False`
- `ALLOWED_HOSTS` set to `.onrender.com`
- `CSRF_TRUSTED_ORIGINS` set to `https://*.onrender.com`
- `SECURE_SSL_REDIRECT=True`

This is consistent with a same-origin live deployment.

## Frontend and CSRF handling

The frontend Axios client in `frontend/src/api/client.ts` is configured to respect an explicit `X-CSRFToken` header instead of overwriting it. That is the correct production-safe behavior for a CSRF-protected session-based deployment.

This matters because the demo auth flow intentionally fetches a CSRF cookie and then posts a strong CSRF token in the same session-scoped flow. The code does not disable CSRF and does not weaken the security boundary.

## Zoho configuration

The application reads Zoho credentials from environment variables instead of embedding them in the repo. The relevant flags are:

- `ZOHO_CLIENT_ID`
- `ZOHO_CLIENT_SECRET`
- `ZOHO_REFRESH_TOKEN`
- `ZOHO_ORG_ID`
- `ZOHO_USE_MOCK`
- `ZOHO_OAUTH_REDIRECT_URI`
- `ZOHO_ALLOWED_REDIRECT_URIS`

Production must set `ZOHO_USE_MOCK=False` and must ensure the callback URIs match the deploy origin exactly. The project defaults to mock mode only for local or demo use; live deployment must not rely on that mode.

## Security audit findings

### Passes

- CSRF protection remains enabled.
- session auth remains enforced.
- demo login is debug-scoped and cannot run outside `DEBUG`.
- backend permission model uses company-scoped and role-based checks.
- secrets are not committed in source files.

### Risks to watch in live deployment

- `render.yaml` must be paired with real environment-variable injection in Render, not just repository defaults.
- `ZOHO_ALLOWED_REDIRECT_URIS` must be updated for the actual deployed frontend host.
- production domains must be added to trust lists and not left at local development values.
- the demo auth endpoints are deliberately disabled outside debug mode and should stay that way.

## Final verdict

The repository is appropriately structured for production deployment, but it remains an environment-dependent deployment. The codebase respects session security, CSRF, and RBAC. The production release is valid if the hosting environment is configured with the real secrets and live callback URLs.
