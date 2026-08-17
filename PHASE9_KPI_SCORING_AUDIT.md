# Phase 9 KPI Scoring Audit

Source reviewed: `core/models/kpi.py`, `core/kpi_service.py`, `core/kpi_scoring_service.py` and KPI tests.

KPI templates define measurement type (NUMERIC, PERCENT, RATING, BOOLEAN or TIME), direction (HIGHER, LOWER or TARGET), defaults, scoring method and min/max score. Framework items snapshot their target/weight into employee assignments; employee overrides ADD, MODIFY or REMOVE resolved items and may be effective-dated.

`KpiScoringService` evaluates assignment measurements, clamps normalized scores to configured score bounds, multiplies each score by assignment weight, and aggregates weighted contributions to a cycle score. No measurement contributes no measured score; cycle summaries preserve the assignment evaluation. Tests cover directional mathematics, clamping, weighted aggregation, framework inheritance and dated ADD/MODIFY/REMOVE overrides.

Boundary evidence is in `core/tests/test_kpi_scoring_engine.py`: 0, target/above-target, lower-is-better behavior, min/max clamping and weighted examples pass. Framework validation rejects invalid GLOBAL/DEPARTMENT/POSITION scope combinations and cross-company queryset references are scoped. The implementation’s exact behavior for negative values and a target of zero is defined by the scoring service tests/implementation rather than a separate HR policy document; HR should approve those cases during UAT before production scoring policy is declared.
