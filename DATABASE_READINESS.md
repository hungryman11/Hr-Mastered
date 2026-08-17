# Database Readiness Audit

## Database pattern

The application uses PostgreSQL in production and falls back to SQLite only for local development and test execution. In `hr_platform/settings.py`, the database is selected based on whether `POSTGRES_DB` is set.

Production path:

- `ENGINE=django.db.backends.postgresql`
- connection values from `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`

Development/test path:

- `ENGINE=django.db.backends.sqlite3`
- database file `db.sqlite3`

## Migration readiness

The project includes the standard Django migrations for core and Zoho modules and has been validated with a full migration cycle during the test run.

Evidence:

- `python manage.py check` returned no issues.
- `python manage.py test core.tests -v 2` created the test database and applied migrations successfully.

## Data model hygiene notes

The codebase includes several model-level protections and workflow guards:

- company-scoped multi-tenancy on critical models
- leave balance validation
- approval step transaction locking for concurrent approval flows
- soft-delete and audit-style patterns for base models

## Production database considerations

For live deployment, the database should be configured with:

- PostgreSQL managed by the platform, not SQLite
- a dedicated service account or user
- automatic backups enabled by the hosting provider
- migration runs performed as part of deployment
- connection secrets stored outside the repo

## Risk assessment

Low risk from the app code itself, provided the live environment uses PostgreSQL and the migrations are run in the deployment pipeline. The main operational risk is configuration drift between development and production environment values.

## Verdict

The database architecture is production-ready when the deployment environment uses PostgreSQL and the migration pipeline is enforced in production.
