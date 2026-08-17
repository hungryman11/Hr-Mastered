from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Optional, Union, Dict, Any
from django.utils import timezone

from core.models import (
    KpiTemplate, EmployeeKpiAssignment, KpiMeasurement, PerformanceCycle, Employee
)


class KpiScoringService:
    @staticmethod
    def _to_decimal(val: Any, default: Decimal = Decimal('0.00')) -> Decimal:
        if val is None or val == '':
            return default
        try:
            return Decimal(str(val).strip().replace(',', ''))
        except (InvalidOperation, ValueError, TypeError):
            return default

    @staticmethod
    def calculate_raw_score(
        measurement_type: str,
        direction: str,
        target: Any,
        actual_value: Any,
    ) -> Decimal:
        """
        Calculate the un-clamped raw score as a percentage (e.g. 100.00 = achieved target).
        """
        if actual_value is None or actual_value == '':
            return Decimal('0.00')

        measurement_type = (measurement_type or '').upper()
        direction = (direction or '').upper()

        # 1. BOOLEAN Measurement
        if measurement_type == KpiTemplate.MeasurementType.BOOLEAN:
            str_val = str(actual_value).strip().lower()
            if str_val in ('true', '1', 'yes', 'achieved', 'pass', 'completed', 't', 'y', 'done'):
                return Decimal('100.00')
            return Decimal('0.00')

        # 2. RATING Measurement (Scale based or Target based)
        if measurement_type == KpiTemplate.MeasurementType.RATING:
            actual_dec = KpiScoringService._to_decimal(actual_value)
            target_dec = KpiScoringService._to_decimal(target)
            if target_dec > Decimal('0'):
                return (actual_dec / target_dec) * Decimal('100.00')
            # Default 5-star scale if target is not defined
            return actual_dec * Decimal('20.00')

        # 3. NUMERIC, PERCENT, TIME Measurements
        actual_dec = KpiScoringService._to_decimal(actual_value)
        target_dec = KpiScoringService._to_decimal(target)

        if target_dec == Decimal('0'):
            if actual_dec == Decimal('0'):
                return Decimal('100.00')
            if direction in (KpiTemplate.Direction.HIGHER_IS_BETTER, 'HIGHER'):
                return Decimal('100.00') if actual_dec > Decimal('0') else Decimal('0.00')
            return Decimal('100.00') if actual_dec <= Decimal('0') else Decimal('0.00')

        if direction in (KpiTemplate.Direction.LOWER_IS_BETTER, 'LOWER'):
            if actual_dec <= Decimal('0'):
                return Decimal('100.00')
            # When lower is better: Target = 200, Actual = 100 -> Score = 200%
            # Target = 200, Actual = 400 -> Score = 50%
            return (target_dec / actual_dec) * Decimal('100.00')

        elif direction in (KpiTemplate.Direction.TARGET_BASED, 'TARGET'):
            # Tolerance-based deviation from target
            diff = abs(actual_dec - target_dec)
            score = Decimal('100.00') - (diff / target_dec) * Decimal('100.00')
            return max(Decimal('0.00'), score)

        else:
            # Default: HIGHER_IS_BETTER
            return (actual_dec / target_dec) * Decimal('100.00')

    @staticmethod
    def normalize_score(
        raw_score: Decimal,
        min_score: Any = Decimal('0.00'),
        max_score: Any = Decimal('100.00'),
    ) -> Decimal:
        """
        Clamp raw score within [min_score, max_score] boundaries and quantize to 2 decimal places.
        """
        min_dec = KpiScoringService._to_decimal(min_score, Decimal('0.00'))
        max_dec = KpiScoringService._to_decimal(max_score, Decimal('100.00'))
        clamped = max(min_dec, min(max_dec, raw_score))
        return clamped.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_weighted_contribution(
        normalized_score: Decimal,
        weight: Any,
    ) -> Decimal:
        """
        Calculate weighted score contribution:
        Weighted Contribution = Normalized Score * (Weight / 100)
        """
        weight_dec = KpiScoringService._to_decimal(weight, Decimal('0.00'))
        contrib = normalized_score * (weight_dec / Decimal('100.00'))
        return contrib.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def evaluate_assignment(
        assignment: EmployeeKpiAssignment,
        actual_value: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate a single assignment's score and weighted contribution.
        """
        snapshot = assignment.full_template_snapshot or {}
        min_score = snapshot.get('min_score', getattr(assignment.template, 'min_score', 0))
        max_score = snapshot.get('max_score', getattr(assignment.template, 'max_score', 100))
        measurement_type = assignment.measurement_type or getattr(assignment.template, 'measurement_type', 'NUMERIC')
        direction = assignment.direction or getattr(assignment.template, 'direction', 'HIGHER')

        if actual_value is None:
            latest_m = assignment.measurements.order_by('-measured_at', '-id').first()
            actual_value = latest_m.value if latest_m else None

        has_measurement = (actual_value is not None and str(actual_value).strip() != '')

        if not has_measurement:
            raw_score = Decimal('0.00')
            normalized_score = Decimal('0.00')
            weighted_contrib = Decimal('0.00')
        else:
            raw_score = KpiScoringService.calculate_raw_score(
                measurement_type=measurement_type,
                direction=direction,
                target=assignment.target,
                actual_value=actual_value,
            )
            normalized_score = KpiScoringService.normalize_score(
                raw_score=raw_score,
                min_score=min_score,
                max_score=max_score,
            )
            weighted_contrib = KpiScoringService.calculate_weighted_contribution(
                normalized_score=normalized_score,
                weight=assignment.weight,
            )

        return {
            'assignment_uuid': str(assignment.uuid),
            'template_name': assignment.template_name or getattr(assignment.template, 'name', ''),
            'measurement_type': measurement_type,
            'direction': direction,
            'target': str(assignment.target),
            'weight': float(assignment.weight),
            'actual_value': str(actual_value) if actual_value is not None else None,
            'has_measurement': has_measurement,
            'min_score': float(min_score),
            'max_score': float(max_score),
            'raw_score': float(raw_score.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            'normalized_score': float(normalized_score),
            'weighted_contribution': float(weighted_contrib),
        }

    @staticmethod
    def evaluate_cycle_for_employee(
        cycle: PerformanceCycle,
        employee: Employee,
    ) -> Dict[str, Any]:
        """
        Evaluate all KPI assignments for an employee within a cycle and calculate
        total performance score and measurement completion rate.
        """
        assignments = EmployeeKpiAssignment.objects.filter(
            cycle=cycle, employee=employee
        ).select_related('template').prefetch_related('measurements')

        evaluations = []
        total_score = Decimal('0.00')
        total_weight = Decimal('0.00')
        measured_count = 0

        for a in assignments:
            res = KpiScoringService.evaluate_assignment(a)
            evaluations.append(res)
            total_score += Decimal(str(res['weighted_contribution']))
            total_weight += Decimal(str(res['weight']))
            if res['has_measurement']:
                measured_count += 1

        total_assignments = len(evaluations)
        completion_rate = (
            round((measured_count / total_assignments) * 100.0, 1)
            if total_assignments > 0 else 0.0
        )

        return {
            'cycle_uuid': str(cycle.uuid),
            'cycle_name': cycle.name,
            'employee_id': employee.id,
            'employee_uuid': str(employee.uuid),
            'employee_name': employee.get_full_name() or employee.username,
            'total_assignments': total_assignments,
            'measured_assignments': measured_count,
            'completion_rate_percent': completion_rate,
            'total_weight': float(total_weight),
            'total_performance_score': float(total_score.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            'assignments': evaluations,
        }
