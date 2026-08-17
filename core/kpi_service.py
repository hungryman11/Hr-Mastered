from typing import Optional
from decimal import Decimal
from django.db import transaction, models
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.models import (
    KpiFramework, KpiTemplate, PerformanceCycle, EmployeeKpiAssignment, Employee, OrgUnit, Position, KpiFrameworkItem, EmployeeKpiOverride
)


class KpiAssignmentService:
    @staticmethod
    def resolve_effective_kpis_for_employee(employee: Employee, as_of_date=None):
        """
        Calculate effective KPIs for an employee by merging:
        GLOBAL -> DEPARTMENT (ancestors root -> leaf) -> POSITION -> EMPLOYEE OVERRIDE (ADD, MODIFY, REMOVE).
        Returns a tuple of (merged_items_dict, total_weight).
        """
        today = as_of_date or timezone.now().date()
        merged = {}

        # 1. Global Frameworks
        global_fws = KpiFramework.objects.filter(
            company=employee.company, scope_type=KpiFramework.ScopeType.GLOBAL, status=KpiFramework.Status.PUBLISHED
        ).order_by('created_at')
        for fw in global_fws:
            for fi in fw.items.all().order_by('sequence'):
                merged[fi.template_id] = {
                    'template_id': fi.template_id,
                    'weight': fi.weight,
                    'target': fi.target,
                    'source': {'scope': 'GLOBAL', 'framework_id': str(fw.uuid), 'framework_name': fw.name}
                }

        # 2. Department Ancestors (root -> leaf)
        unit = employee.org_unit
        ancestors = []
        visited = set()
        while unit and unit.pk not in visited:
            visited.add(unit.pk)
            ancestors.append(unit)
            unit = unit.parent
        ancestors.reverse()

        for u in ancestors:
            dept_fws = KpiFramework.objects.filter(
                company=employee.company, scope_type=KpiFramework.ScopeType.DEPARTMENT, org_unit=u, status=KpiFramework.Status.PUBLISHED
            ).order_by('created_at')
            for fw in dept_fws:
                for fi in fw.items.all().order_by('sequence'):
                    merged[fi.template_id] = {
                        'template_id': fi.template_id,
                        'weight': fi.weight,
                        'target': fi.target,
                        'source': {'scope': 'DEPARTMENT', 'org_unit_id': u.id, 'org_unit_name': u.name, 'framework_id': str(fw.uuid)}
                    }

        # 3. Position Framework
        if employee.position_id:
            pos_fws = KpiFramework.objects.filter(
                company=employee.company, scope_type=KpiFramework.ScopeType.POSITION, position=employee.position, status=KpiFramework.Status.PUBLISHED
            ).order_by('created_at')
            for fw in pos_fws:
                for fi in fw.items.all().order_by('sequence'):
                    merged[fi.template_id] = {
                        'template_id': fi.template_id,
                        'weight': fi.weight,
                        'target': fi.target,
                        'source': {'scope': 'POSITION', 'position_id': employee.position_id, 'position_title': employee.position.title, 'framework_id': str(fw.uuid)}
                    }

        # 4. Employee-level Overrides (Highest precedence)
        overrides = EmployeeKpiOverride.objects.filter(
            company=employee.company,
            employee=employee,
            active=True,
        ).filter(
            models.Q(effective_from__isnull=True) | models.Q(effective_from__lte=today),
            models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=today),
        )

        for ov in overrides:
            if ov.action_type == EmployeeKpiOverride.ActionType.REMOVE:
                merged.pop(ov.template_id, None)
            else:
                merged[ov.template_id] = {
                    'template_id': ov.template_id,
                    'weight': ov.weight,
                    'target': ov.target,
                    'source': {'scope': 'EMPLOYEE_OVERRIDE', 'override_id': ov.id, 'action': ov.action_type}
                }

        total_weight = sum((Decimal(str(item['weight'] or 0)) for item in merged.values()), Decimal('0'))
        return merged, total_weight

    @staticmethod
    def get_effective_kpis_preview(employee: Employee, as_of_date=None):
        """
        Return structured preview of effective KPIs for an employee with full metadata,
        provenance source tags, weight validation, and issue diagnostics.
        """
        today = as_of_date or timezone.now().date()
        merged, total_weight = KpiAssignmentService.resolve_effective_kpis_for_employee(employee, as_of_date=today)

        template_ids = list(merged.keys())
        templates = {
            t.id: t for t in KpiTemplate.objects.filter(
                id__in=template_ids, company=employee.company
            ).select_related('category')
        }

        items = []
        for tid, data in merged.items():
            tmpl = templates.get(tid)
            if not tmpl:
                continue
            items.append({
                'template_id': tmpl.id,
                'template_uuid': str(tmpl.uuid),
                'template_name': tmpl.name,
                'template_description': tmpl.description,
                'category_id': tmpl.category_id,
                'category_name': tmpl.category.name if tmpl.category else '',
                'measurement_type': tmpl.measurement_type,
                'direction': tmpl.direction,
                'scoring_method': tmpl.scoring_method,
                'min_score': float(tmpl.min_score),
                'max_score': float(tmpl.max_score),
                'target': str(data.get('target', tmpl.default_target)),
                'weight': float(data.get('weight', tmpl.default_weight)),
                'source': data.get('source', {}),
            })

        is_valid = abs(total_weight - Decimal('100')) <= Decimal('0.01')
        issues = []
        if not items:
            issues.append("No active KPIs configured for this employee.")
        elif not is_valid:
            issues.append(f"Total resolved weight is {total_weight}%, but must equal 100%.")

        return {
            'employee_id': employee.id,
            'employee_uuid': str(employee.uuid),
            'employee_name': employee.get_full_name() or employee.username,
            'department_name': employee.org_unit.name if employee.org_unit else '',
            'position_title': employee.position.title if employee.position else '',
            'as_of_date': str(today),
            'total_weight': float(total_weight),
            'is_valid_total_weight': is_valid,
            'items_count': len(items),
            'items': items,
            'issues': issues,
        }

    @staticmethod
    def preview_cycle_assignments(cycle: PerformanceCycle):
        """
        Return company-wide preview of assignment generation for all active employees
        in the cycle's company, summarizing valid vs invalid assignments.
        """
        employees = Employee.objects.filter(
            company=cycle.company, is_active=True
        ).select_related('org_unit', 'position')
        previews = []
        valid_count = 0
        invalid_count = 0

        for emp in employees:
            preview = KpiAssignmentService.get_effective_kpis_preview(emp, as_of_date=cycle.start_date)
            if preview['items_count'] > 0:
                if preview['is_valid_total_weight']:
                    valid_count += 1
                else:
                    invalid_count += 1
            previews.append(preview)

        can_generate = (invalid_count == 0) and (valid_count > 0)
        return {
            'cycle_uuid': str(cycle.uuid),
            'cycle_name': cycle.name,
            'as_of_date': str(cycle.start_date),
            'total_employees': len(employees),
            'valid_employees': valid_count,
            'invalid_employees': invalid_count,
            'can_generate_assignments': can_generate,
            'previews': previews,
        }

    @staticmethod
    @transaction.atomic
    def generate_assignments_for_cycle(cycle: PerformanceCycle):
        employees = Employee.objects.filter(company=cycle.company, is_active=True)
        created = []
        for emp in employees:
            merged, total_weight = KpiAssignmentService.resolve_effective_kpis_for_employee(emp, as_of_date=cycle.start_date)

            if not merged:
                continue

            if abs(total_weight - Decimal('100')) > Decimal('0.01'):
                raise ValidationError(
                    f"Cannot create assignments for employee {emp.get_full_name() or emp.username}: "
                    f"Resolved KPI weights total {total_weight}%, but must sum to 100%."
                )

            for template_id, data in merged.items():
                try:
                    tmpl = KpiTemplate.objects.get(pk=template_id, company=cycle.company)
                except KpiTemplate.DoesNotExist:
                    continue
                defaults = {
                    'target': data.get('target', tmpl.default_target),
                    'weight': data.get('weight', tmpl.default_weight),
                    'source': data.get('source', {}),
                    'template_name': tmpl.name,
                    'measurement_type': tmpl.measurement_type,
                    'direction': tmpl.direction,
                    'scoring_method': tmpl.scoring_method,
                    'category_name': tmpl.category.name if tmpl.category else '',
                    'template_description': tmpl.description,
                    'template_default_target': tmpl.default_target,
                    'template_default_weight': tmpl.default_weight,
                    'template_frequency': tmpl.frequency,
                    'template_data_source': tmpl.data_source,
                    'full_template_snapshot': {
                        'id': str(tmpl.uuid),
                        'name': tmpl.name,
                        'description': tmpl.description,
                        'measurement_type': tmpl.measurement_type,
                        'direction': tmpl.direction,
                        'scoring_method': tmpl.scoring_method,
                        'min_score': float(tmpl.min_score),
                        'max_score': float(tmpl.max_score),
                        'category': {
                            'id': str(tmpl.category.uuid) if tmpl.category else None,
                            'name': tmpl.category.name if tmpl.category else None,
                        },
                        'default_target': tmpl.default_target,
                        'default_weight': float(tmpl.default_weight),
                        'frequency': tmpl.frequency,
                        'data_source': tmpl.data_source,
                    },
                }
                assignment, created_flag = EmployeeKpiAssignment.objects.get_or_create(
                    company=cycle.company,
                    cycle=cycle,
                    employee=emp,
                    template=tmpl,
                    defaults=defaults,
                )
                if not created_flag:
                    assignment.target = data.get('target', assignment.target)
                    assignment.weight = data.get('weight', assignment.weight)
                    assignment.source = assignment.source or {}
                    assignment.source.update(data.get('source', {}))
                    assignment.save()
                created.append(assignment)
        return created

