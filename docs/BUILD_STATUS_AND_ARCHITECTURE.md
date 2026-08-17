# Hr-Mastered: Build Status, System Architecture, and Technical Reference

This document tracks the technical implementation status and architectural reference for the **Hr-Mastered** platform.

---

## 1. Build Status Summary

| Module | Build Phase | Status | Test Coverage |
|---|---|---|---|
| **Core Data Model & Organogram** | Phase 1 | Complete ✅ | 39 tests |
| **Tenant Isolation & Security** | Phase 2 | Complete ✅ | 6 tests |
| **Leave Management & 2-Stage Approvals** | Phase 3 | Complete ✅ | 61 tests |
| **KPI Inheritance & Dynamic Overrides** | Phase 4 | Complete ✅ | 5 tests |
| **KPI Scoring Engine & Formulas** | Phase 5 | Complete ✅ | 5 tests |
| **Performance Review & Calibration** | Phase 6 | Complete ✅ | 4 tests |
| **Salary History & Compensation** | Phase 7 | Complete ✅ | 16 tests |
| **Frontend UI Refactoring** | Phase 8 | Planned / Designed 📋 | Vitest suite |
| **Final Documentation & Cleanup** | Phase 9 | Complete ✅ | 136 backend tests passing |

**Total Backend Test Count**: 136 tests (100% pass rate).

---

## 2. Architecture & Data Model

### 2.1 Multi-Tenancy & Organogram
- All core entities inherit from `CompanyScopedModel`, enforcing tenant isolation at both the ORM and REST viewset level.
- `OrgUnit` supports recursive hierarchies (e.g. Division $\rightarrow$ Department $\rightarrow$ Unit) with designated unit heads.
- `Position` links employees to standardized job roles.

### 2.2 Leave Management Lifecycle
- 2-stage approval routing: `Stage 1: Department Head` $\rightarrow$ `Stage 2: HR Admin`.
- Concurrency control via database `select_for_update()` row locking on balance mutations.
- `ApprovalDecision` records are write-once and immutable.
- `ApprovalDelegation` provides temporary approval authority scoped strictly within the active company tenant.

### 2.3 KPI Engine & Scoring Rules
- **Inheritance Resolution**: Global Framework $\rightarrow$ Department Framework $\rightarrow$ Position Framework $\rightarrow$ Employee Overrides (`ADD`, `MODIFY`, `REMOVE`).
- **Scoring Formulas**:
  - `HIGHER_IS_BETTER`: $(\text{Actual} / \text{Target}) \times 100$
  - `LOWER_IS_BETTER`: $(\text{Target} / \text{Actual}) \times 100$
  - `TARGET_BASED`: $\max(0, 100 - (\text{Deviation} / \text{Target}) \times 100)$
  - `BOOLEAN`: $100.00$ if achieved, $0.00$ otherwise
  - `RATING`: Scaled / 5-star normalized
- Clamped between $[\text{min\_score}, \text{max\_score}]$ and weighted by $(\text{Weight} / 100)$.

### 2.4 Performance Review Lifecycle
- Status State Machine: `DRAFT` $\rightarrow$ `SUBMITTED` $\rightarrow$ `MANAGER_REVIEWED` $\rightarrow$ `HR_REVIEWED` $\rightarrow$ `CALIBRATED` $\rightarrow$ `FINALIZED`.
- Finalized reviews are strictly immutable.

### 2.5 Salary History & Allowances
- Structured components: `base_salary`, `housing_allowance`, `transport_allowance`, `meal_allowance`, `other_allowances`.
- Computed `gross_salary` property.
- Overlap prevention validation across date ranges for active records.
- Supersede endpoint for atomic salary revision.

---

## 3. Test Suite Verification

```powershell
python manage.py test core --verbosity=1
```
Result: **136 tests passed**.
