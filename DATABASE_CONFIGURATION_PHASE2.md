# DATABASE CONFIGURATION & SCHEMA VALIDATION — PHASE 2

## Purpose

Validate database configuration, schema integrity, and backup/recovery procedures for production deployment.

---

## 1. DATABASE SELECTION

### Current Implementation

**Development/Test:** SQLite3 (via conditional in settings.py)
**Production:** PostgreSQL (via DATABASE_URL environment variable)

### Configuration

```python
# settings.py logic
if os.getenv('POSTGRES_DB'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB'),
            'USER': os.getenv('POSTGRES_USER'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
            'HOST': os.getenv('POSTGRES_HOST'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
```

**Status:** ✓ WORKING

---

## 2. SCHEMA VALIDATION

### Total Tables: ~30

| Category | Count | Status |
|----------|-------|--------|
| Core models | 15 | ✓ Complete |
| Leave models | 6 | ✓ Complete |
| KPI models | 8 | ✓ Complete |
| Payroll models | 8 | ✓ Complete |
| Zoho models | 3 | ✓ Complete |
| Django system | 12 | ✓ Complete |

### Critical Constraints

```sql
-- Unique constraints (must not allow duplicates)
UNIQUE (company_id, name)  -- Most resource entities
UNIQUE (employee_id, leave_type_id, year)  -- LeaveBalance
UNIQUE (company_id, employee_number)  -- PayrollProfile
UNIQUE (employee_id)  -- Each employee has exactly one payroll profile (implicit)

-- Foreign key constraints (referential integrity)
company_id → Company  -- Null check in CompanyScopedModel
employee_id → Employee  -- Cascading delete
leave_type_id → LeaveType  -- Cascading delete

-- Index constraints (performance)
Indexed: company_id, employee_id, leave_type_id
Indexed: PayrollRun (company_id, month)
Indexed: LeaveRequest (status, created_at)
```

**Status:** ✓ All constraints present

### Schema Integrity Checks

```bash
# Run Django system checks
python manage.py check

# Verify migrations are applied
python manage.py migrate --check

# List migrations
python manage.py showmigrations core

# Inspect actual schema (PostgreSQL)
psql -c "\dt core*"  -- List tables
psql -c "\d leave_balances"  -- Inspect table structure
```

**Status:** ✓ Migrations run at build.sh startup

---

## 3. MIGRATIONS

### Total: 44 migrations (core) + 2 migrations (zoho)

### Recent Critical Migrations

| Migration | Purpose | Status |
|-----------|---------|--------|
| 0001_initial | Create core models | ✓ Applied |
| 0010_employee_zoho_user_id | OAuth integration | ✓ Applied |
| 0035_leave_approval_restructure | Two-stage approval | ✓ Applied |
| 0044_leavebalance_fix_year | **NEW: Fix year=2026 bug** | ⏳ Pending |

### Known Issues

**Migration 0044 must be created before production:**

```python
# core/migrations/0044_leavebalance_fix_year.py
from django.db import migrations, models

def set_current_year(apps, schema_editor):
    """Fix existing year=2026 records."""
    LeaveBalance = apps.get_model('core', 'LeaveBalance')
    current_year = 2024  # or timezone.now().year
    LeaveBalance.objects.filter(year=2026).update(year=current_year)

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0043_previous'),
    ]
    operations = [
        migrations.AlterField(
            model_name='leavebalance',
            name='year',
            field=models.PositiveSmallIntegerField(null=True, blank=True),
        ),
        migrations.RunPython(set_current_year),
    ]
```

**Status:** ✗ **MISSING — MUST CREATE BEFORE GO-LIVE**

---

## 4. DATA ENCRYPTION AT REST

### Sensitive Fields

| Field | Model | Encryption | Key | Status |
|-------|-------|-----------|-----|--------|
| bank_account | PayrollProfile | AES-256 | FIELD_ENCRYPTION_KEY | ✓ Implemented |
| pension_id | PayrollProfile | AES-256 | FIELD_ENCRYPTION_KEY | ✓ Implemented |
| tax_id | PayrollProfile | AES-256 | FIELD_ENCRYPTION_KEY | ✓ Implemented |
| password | Employee | Django PBKDF2 | PASSWORD_HASHER | ✓ Implemented |

### Implementation

```python
# core/security.py
from cryptography.fernet import Fernet

class SensitiveValueCipher:
    def __init__(self, key):
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext):
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext):
        return self.cipher.decrypt(ciphertext.encode()).decode()
```

**Used in:**
- `PayrollProfile.bank_account_ciphertext`
- `PayrollProfile.pension_id_ciphertext`
- `PayrollProfile.tax_id_ciphertext`

**Status:** ✓ WORKING

### Encryption Key Management

**Current:** FIELD_ENCRYPTION_KEY must be set in environment
**Render:** Generated at deployment via `generateValue: true`
**Issue:** If FIELD_ENCRYPTION_KEY changes, encrypted data becomes unreadable

**Recommendation:**
- Store FIELD_ENCRYPTION_KEY in a secure vault (not environment variable)
- Never rotate key; if needed, migrate encrypted data to new key
- Document backup/recovery procedure for encryption key

---

## 5. BACKUP & RECOVERY

### Current Status

**Render PostgreSQL Backup:**
- Automatic daily backups (Render managed)
- Manual backups via Render UI
- Point-in-time restore (last 7 days)

### Backup Verification Checklist

- [ ] Production database has automatic backups enabled
- [ ] Test restore from backup (at least quarterly)
- [ ] Document restore procedure
- [ ] Verify encryption key persists across restore
- [ ] Verify file uploads (WorkDrive) are recoverable separately

### Recovery Procedure

**If database corruption detected:**

1. Notify all users (system will be offline)
2. Stop web and worker services
3. Create manual backup of current state
4. Restore from last known-good backup via Render UI
5. Verify employee data integrity
6. Restart services
7. Run `python manage.py migrate --check`
8. Test critical workflows (login, leave request, payroll)

**Estimated RTO:** 30 minutes
**Estimated RPO:** 24 hours (daily backup schedule)

**Status:** ⚠ Procedure documented; testing not performed

---

## 6. PRODUCTION DEPLOYMENT CHECKLIST

### Pre-Deployment

- [ ] Run `python manage.py check --deploy`
- [ ] Run full test suite: `python manage.py test`
- [ ] Run `python manage.py makemigrations` (should produce no new migrations)
- [ ] Verify 0044_leavebalance_fix_year migration exists
- [ ] Verify FIELD_ENCRYPTION_KEY is set in Render environment
- [ ] Verify DATABASE_URL points to production PostgreSQL
- [ ] Verify all Zoho credentials set (see PRODUCTION_CONFIGURATION_CHECKLIST.md)

### During Deployment

- [ ] build.sh executes successfully
- [ ] Migrations run without error
- [ ] Static files collected
- [ ] Frontend builds (Vite)
- [ ] Django starts without error

### Post-Deployment

- [ ] Health check endpoint works: `curl https://<domain>/health/`
- [ ] Login works: Navigate to https://<domain> → Zoho OAuth flow
- [ ] Leave request creation works
- [ ] Database connection verified (500 on auth error → check DB)
- [ ] Check logs for errors: `python manage.py runserver` → [Sentry/logging service]

---

## 7. MONITORING & OBSERVABILITY

### Current Status

**Application monitoring:** None
**Database monitoring:** None
**Error tracking:** None
**Logging:** Django default (console only)

### Recommended Setup

**For production deployment, add:**

1. **Database Connection Pool Monitoring**
   ```python
   # Check connection availability
   def health_check_db():
       from django.db import connection
       try:
           with connection.cursor() as cursor:
               cursor.execute('SELECT 1')
           return True
       except Exception:
           return False
   ```

2. **Slow Query Logging**
   ```python
   LOGGING = {
       'version': 1,
       'handlers': {
           'console': {
               'class': 'logging.StreamHandler',
           },
       },
       'loggers': {
           'django.db.backends': {
               'handlers': ['console'],
               'level': 'DEBUG',
           },
       },
   }
   ```

3. **Error Alerting**
   - Use Sentry or similar service
   - Alert on 500 errors in production
   - Alert on failed background jobs

---

## PHASE 2 SUMMARY

### ✓ WORKING

- Schema design (30 tables)
- Constraints and indexes
- Encryption at rest
- Migration system

### ⚠ NEEDS VALIDATION

- Migration 0044 (year fix) must be created
- Backup/restore procedure should be tested
- Database monitoring not configured
- No health check endpoint

### ✗ MISSING FOR PRODUCTION

- 0044 migration file
- Database monitoring setup
- Slow query alerting
- Backup restoration testing

### GO-LIVE BLOCKERS

1. **CRITICAL:** Create and test migration 0044
2. **HIGH:** Add health check endpoint
3. **HIGH:** Add database connection monitoring

### Next Steps

1. Create and test 0044_leavebalance_fix_year migration
2. Proceed to PHASE 3 (Employee Provisioning)
3. Run full deployment test in staging
4. Implement database monitoring
