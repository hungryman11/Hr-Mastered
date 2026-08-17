import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError

from core.models import Company, PayrollProfile


class PayrollImportService:
    @staticmethod
    def validate_profile_csv(company, csv_stream):
        raw = csv_stream.read()
        # Uploaded files (Django's InMemoryUploadedFile/TemporaryUploadedFile) yield bytes,
        # not str, so this always failed with "initial_value must be str or None, not
        # bytes" for any real upload - it only "passed" in isolation if ever called with
        # a str directly. utf-8-sig also quietly strips the BOM Excel adds to CSV exports.
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(raw))
        required = {'employee_number', 'base_salary', 'bank_code', 'hire_date'}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValidationError('Payroll CSV must include employee_number, base_salary, bank_code, and hire_date columns.')

        valid_rows = []
        errors = []
        for line_number, row in enumerate(reader, start=2):
            issues = []
            employee_number = (row.get('employee_number') or '').strip()
            base_salary = (row.get('base_salary') or '').strip()
            bank_code = (row.get('bank_code') or '').strip()
            hire_date = (row.get('hire_date') or '').strip()
            if not employee_number:
                issues.append('employee_number')
            if not bank_code or not bank_code.isdigit() or len(bank_code) != 3:
                issues.append('bank_code')
            try:
                salary = Decimal(base_salary)
                if salary <= 0:
                    issues.append('base_salary')
            except (InvalidOperation, TypeError):
                issues.append('base_salary')
            try:
                datetime.strptime(hire_date, '%Y-%m-%d')
            except (TypeError, ValueError):
                issues.append('hire_date')
            if issues:
                errors.append({'line_number': line_number, 'row': row, 'issues': issues})
                continue
            valid_rows.append({
                'employee_number': employee_number,
                'base_salary': salary,
                'bank_code': bank_code,
                'hire_date': hire_date,
            })
        return valid_rows, errors

    @staticmethod
    def import_profiles(company: Company, csv_stream):
        valid_rows, errors = PayrollImportService.validate_profile_csv(company, csv_stream)
        if errors:
            raise ValidationError({'rows': errors})

        updated = 0
        for row in valid_rows:
            profile = PayrollProfile.objects.filter(company=company, employee_number=row['employee_number']).first()
            if profile is None:
                raise ValidationError({'employee_number': f'No payroll profile exists for employee_number={row["employee_number"]}.'})
            profile.base_salary = row['base_salary']
            profile.bank_code = row['bank_code']
            profile.hire_date = datetime.strptime(row['hire_date'], '%Y-%m-%d').date()
            profile.save(update_fields=['base_salary', 'bank_code', 'hire_date', 'updated_at'])
            updated += 1
        return updated
