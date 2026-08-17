# Production Environment Variables

This document lists the environment variables actually consumed by the application and how they should be configured for production.

| Variable | Required | Secret | Purpose | Example format | Where configured |
| --- | --- | --- | --- | --- | --- |
| `APP_ENV` | Yes | No | Switches behavior between local development and production validation. | `production` | Render / hosting env |
| `DEBUG` | Yes | No | Must be `False` in production. | `False` | Render / hosting env |
| `SECRET_KEY` | Yes | Yes | Django secret used for signing and sessions. | `s3cr3t-...-64+chars` | Render secret env |
| `FIELD_ENCRYPTION_KEY` | Yes | Yes | Dedicated Fernet encryption key for payroll fields. | `A1b2C3d4E5f6G7h8...` | Render secret env |
| `DATABASE_URL` | Yes | Yes | PostgreSQL connection string. | `postgres://user:pass@host:5432/dbname` | Render database env |
| `ALLOWED_HOSTS` | Yes | No | Real production domains only. | `app.example.com,api.example.com` | Render env |
| `CSRF_TRUSTED_ORIGINS` | Yes | No | HTTPS origins allowed to submit CSRF. | `https://app.example.com,https://api.example.com` | Render env |
| `SECURE_SSL_REDIRECT` | Yes | No | Forces HTTPS for all traffic. | `True` | Render env |
| `SESSION_COOKIE_SECURE` | Yes | No | Protects session cookies over HTTPS only. | `True` | Render env |
| `CSRF_COOKIE_SECURE` | Yes | No | Protects CSRF cookies over HTTPS only. | `True` | Render env |
| `SECURE_HSTS_SECONDS` | Yes | No | HTTP Strict Transport Security duration. | `31536000` | Render env |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | Yes | No | Applies HSTS to subdomains. | `True` | Render env |
| `SECURE_HSTS_PRELOAD` | Yes | No | Enables browser preload eligibility. | `True` | Render env |
| `ZOHO_CLIENT_ID` | Yes | Yes | Zoho OAuth client ID. | `1000.xxxxxxxxx` | Render secret env |
| `ZOHO_CLIENT_SECRET` | Yes | Yes | Zoho OAuth client secret. | `abc123...` | Render secret env |
| `ZOHO_REFRESH_TOKEN` | Yes | Yes | Refresh token for Zoho API access. | `1000.x...` | Render secret env |
| `ZOHO_ORG_ID` | Recommended | Yes | Zoho org identifier for API calls. | `123456789` | Render secret env |
| `ZOHO_OAUTH_REDIRECT_URI` | Yes | No | Exact callback URL registered in Zoho. | `https://app.example.com/app/callback` | Render env |
| `ZOHO_ALLOWED_REDIRECT_URIS` | Yes | No | Comma-separated allow-list of exact registered callback URLs. | `https://app.example.com/app/callback` | Render env |
| `ZOHO_USE_MOCK` | No | No | Enables mock Zoho mode for dev/test only. | `False` | Render env |
| `ZOHO_LOGIN_SCOPES` | No | No | OAuth scopes requested from Zoho. | `AaaServer.profile.READ` | Render env |
| `ZOHO_ALLOWED_EMAIL_DOMAIN` | No | No | Restricts login to a specific corporate email domain. | `example.com` | Render env |
| `EMAIL_HOST` | Yes | No | SMTP server host. | `smtp.zoho.com` | Render env |
| `EMAIL_HOST_USER` | Yes | Yes | SMTP username / email address. | `noreply@example.com` | Render secret env |
| `EMAIL_HOST_PASSWORD` | Yes | Yes | SMTP app password. | `abcd-1234` | Render secret env |
| `EMAIL_PORT` | No | No | SMTP port. | `587` | Render env |
| `EMAIL_USE_TLS` | No | No | SMTP TLS flag. | `True` | Render env |
| `DEFAULT_FROM_EMAIL` | Yes | No | Verified sender address. | `noreply@example.com` | Render env |
| `MEDIA_ROOT` | Yes | No | Local or mounted directory for uploaded files. | `/var/www/media` | Render env |
| `STATIC_ROOT` | Yes | No | Output path for static assets. | `/var/www/static` | Render env |

Notes:
- Never commit secret values into the repository.
- Render secret env vars should be stored in the service configuration as environment variables or secrets, not embedded in YAML.
- The callback URI must exactly match the Zoho Console registration, including scheme, host, and path.
