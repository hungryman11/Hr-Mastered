# Hr-Mastered: Complete Live Setup & Role-Based User Manual

> [!NOTE]
> This document provides a complete, step-by-step operational guide for initializing, configuring, deploying, and using the **Hr-Mastered** HR, Payroll, and Loan Compliance Platform.

---

## Table of Contents

1. [Architecture & System Overview](#1-architecture--system-overview)
2. [Step-by-Step Live Production Setup Guide](#2-step-by-step-live-production-setup-guide)
   - [Local Development Setup](#local-development-setup)
   - [Live Cloud Deployment (Render.com + PostgreSQL)](#live-cloud-deployment-rendercom--postgresql)
   - [Zoho Integration Setup](#zoho-integration-setup)
3. [System Administration & Initial Onboarding](#3-system-administration--initial-onboarding)
4. [Role-Based Operating Manual](#4-role-based-operating-manual)
   - [Role Matrix & Access Control](#role-matrix--access-control)
   - [HR Admin Guide](#1-hr-admin-guide)
   - [Finance User Guide](#2-finance-user-guide)
   - [Risk Checker Guide](#3-risk-checker-guide)
   - [Compliance Admin Guide](#4-compliance-admin-guide)
   - [General Employee Guide](#5-general-employee-guide)
5. [End-to-End Operational Workflows](#5-end-to-end-operational-workflows)
   - [Monthly Payroll Cycle Execution](#workflow-a-monthly-payroll-cycle-execution)
   - [Loan Case Compliance & Approval Cycle](#workflow-b-loan-case-compliance--approval-cycle)

---

## 1. Architecture & System Overview

Hr-Mastered is structured around strict company multi-tenancy, role-based access control (RBAC), and background task processing:

- **Backend**: Django 5.x REST Framework API with PostgreSQL.
- **Frontend**: React + Vite single-page application.
- **Delivery Worker**: Dedicated worker process (`python manage.py run_delivery_worker`) handling asynchronous email notifications and document uploads to Zoho WorkDrive.
- **Security**: AES-256 field encryption (`SensitiveValueCipher`) for sensitive data (bank account details, tax IDs).

---

## 2. Step-by-Step Live Production Setup Guide

### Local Development Setup

#### Prerequisites
- Python 3.12+
- Node.js 18+ & `npm`
- PostgreSQL 16+ (or SQLite for local dev)

#### Installation Steps

1. **Clone repository and set up virtual environment**:
   ```bash
   git clone <repository-url>
   cd Hr-Mastered
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Configure Environment Variables**:
   Create a `.env` file in the root directory:
   ```ini
   SECRET_KEY=your-django-secret-key-here
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   DATABASE_URL=postgres://hr_user:hr_pass@localhost:5432/hr_mastered
   FIELD_ENCRYPTION_KEY=your-32-byte-base64-encryption-key
   
   # Zoho Integration Credentials
   ZOHO_CLIENT_ID=your-zoho-client-id
   ZOHO_CLIENT_SECRET=your-zoho-client-secret
   ZOHO_REFRESH_TOKEN=your-zoho-refresh-token
   ZOHO_ORG_ID=your-zoho-org-id
   ZOHO_OAUTH_REDIRECT_URI=http://localhost:8000/api/zoho/auth/callback/
   ```

4. **Run Database Migrations & Seed Data**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Start Frontend & Backend Servers**:
   ```bash
   # Terminal 1: Backend Django Server
   python manage.py runserver 8000

   # Terminal 2: Background Delivery Worker
   python manage.py run_delivery_worker

   # Terminal 3: Frontend Development Server
   cd frontend
   npm install
   npm run dev
   ```

---

### Live Cloud Deployment (Render.com + PostgreSQL)

The platform is pre-configured for automated blueprint deployment on Render.com.

#### Step 1: Provision Render Resources
1. Log in to [Render Dashboard](https://dashboard.render.com/).
2. Select **New +** -> **Blueprint**.
3. Connect your Git repository. Render will automatically detect `render.yaml`.
4. Render will initialize 3 managed resources:
   - `hr-mastered-db` (PostgreSQL Database)
   - `hr-mastered-web` (Web Service running Gunicorn)
   - `hr-mastered-worker` (Background worker service running `python manage.py run_delivery_worker`)

#### Step 2: Set Environment Variables
In the Render Web Service settings, populate the required environment variables:
- `SECRET_KEY`: Generate a random 50+ character string.
- `FIELD_ENCRYPTION_KEY`: A secure 32-character key for Fernet payload encryption.
- `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_REFRESH_TOKEN`, `ZOHO_ORG_ID`.
- `ZOHO_OAUTH_REDIRECT_URI`: Set to `https://<your-web-service>.onrender.com/api/zoho/auth/callback/`.

#### Step 3: Run Initial Migrations & Create Superuser
In the Render Web Service Shell:
```bash
python manage.py migrate
python manage.py createsuperuser
```

---

### Zoho Integration Setup

1. Log into the [Zoho API Console](https://api-console.zoho.com/).
2. Register a new **Server-based Application**.
3. Set the Redirect URI to `https://<your-domain>/api/zoho/auth/callback/`.
4. Obtain `Client ID` and `Client Secret`.
5. Generate a `Refresh Token` with scopes for Zoho Mail and Zoho WorkDrive:
   `ZohoMail.messages.CREATE,ZohoMail.messages.UPDATE,WorkDrive.workspace.ALL,WorkDrive.files.ALL`
6. Save credentials to your live server environment variables.

---

## 3. System Administration & Initial Onboarding

When setting up a new organization in Hr-Mastered:

1. **Create Company**: Log in as a Django Superuser at `/admin/` and navigate to **Companies** -> **Add Company**.
2. **Create Primary HR Admin User**: Create an `Employee` account with role `HR_ADMIN` linked to the newly created Company.
3. **Set Payroll Configuration**:
   - Navigate to `/api/payroll-configs/` (or via Admin panel).
   - Define maximum allowed deduction percentage (e.g. `30%`).
   - Configure enabled settlement formats (`["CSV", "XLSX", "PDF"]`).
4. **Define Statutory Rules**:
   - Add rules for Tax (PAYE), Pension, National Health Insurance, etc.

---

## 4. Role-Based Operating Manual

### Role Matrix & Access Control

| Feature / Module | Superuser | HR Admin | Finance | Risk Checker | Compliance Admin | Employee |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Manage Profiles & Import CSV** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Calculate Payroll Run** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Review & Approve Payroll Run** | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Export Settlement Pack** | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Bank Reconciliation** | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Contest Deduction** | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ (Own) |
| **Resolve Deduction Dispute** | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Create Loan Products & Templates**| ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Create Loan Case** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Verify Checklist Evidence** | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Final Loan Approval/Rejection** | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |

---

### 1. HR Admin Guide

#### Tasks & Responsibilities
- Employee onboarding and payroll profile creation.
- Bulk uploading payroll profiles via CSV.
- Initiating monthly payroll runs.
- Setting up loan products and required evidence checklists.

#### Step-by-Step Instructions

##### A. Creating a Payroll Profile
1. Navigate to **Payroll Profiles** -> **New Profile**.
2. Select the **Employee** from your company.
3. Enter **Employee Number**, **Base Salary**, **Hire Date**, **Bank Code**, and **Account Number**.
4. Click **Save Profile**. *(Bank details are automatically encrypted upon saving).*

##### B. Bulk Importing Profiles via CSV
1. Go to **Payroll Profiles** -> **Import CSV**.
2. Upload your CSV file structured as follows:
   ```csv
   employee_number,base_salary,bank_code,hire_date
   EMP-001,85000.00,058,2025-01-15
   EMP-002,92000.00,033,2025-02-01
   ```
3. Click **Validate CSV**. The system will verify row formats without persisting.
4. Review valid count and error table. Once zero errors remain, click **Import**.

##### C. Creating Loan Products & Checklists
1. Go to **Loan Products** -> **Create Product**.
2. Name the product (e.g., "Emergency Staff Loan").
3. Add **Checklist Items** (e.g., "National ID", "3-Month Bank Statement", "Guarantor Letter"). Mark required items accordingly.
4. Save the product.

---

### 2. Finance User Guide

#### Tasks & Responsibilities
- Reviewing and approving monthly payroll runs.
- Exporting settlement payment packs for bank execution.
- Reconciling bank settlement outcomes.
- Resolving employee deduction disputes.

#### Step-by-Step Instructions

##### A. Reviewing & Approving Payroll
1. Navigate to **Payroll Runs**.
2. Select a run in `CALCULATED` status.
3. Review total gross pay, statutory deductions, net pay totals, and line items.
4. Click **Mark Reviewed** (Status changes to `REVIEWED`).
5. Click **Approve Payroll** (Status changes to `APPROVED`).
   > [!IMPORTANT]
   > Maker-Checker Policy: The user who calculated the payroll run cannot approve it.

##### B. Exporting Settlement Packs
1. Open an `APPROVED` payroll run.
2. Click **Export Settlement Pack**.
3. Select format (`CSV`, `XLSX`, `PDF`, or `PACK` for all three).
4. Download files. Verify generated SHA-256 checksums match your bank delivery records.

##### C. Bank Reconciliation
1. Once bank payments complete, open the `EXPORTED` payroll run.
2. Click **Reconcile**.
3. Select Outcome: **SUCCESS** or **FAILED**.
4. Enter Bank Transaction Reference (e.g., `TRX-9948201`) and execution date.
5. Click **Submit Reconciliation**.

##### D. Resolving Deduction Disputes
1. Go to **Deduction Disputes**.
2. Select a contested deduction flagged as `IS_HELD`.
3. Review employee's dispute reason.
4. Click **Resolve**:
   - **Uphold**: Deduction stands; amount is retained.
   - **Remove**: Deduction is cleared to `0.00`, and employee net pay is restored.
5. Enter mandatory **Resolution Notes** and confirm.

---

### 3. Risk Checker Guide

#### Tasks & Responsibilities
- Reviewing applicant evidence for loan cases.
- Verifying checklist documentation.
- Recording evidence reference IDs and audit notes.

#### Step-by-Step Instructions

1. Navigate to **Loan Cases** -> **In Review**.
2. Select an active loan case.
3. For each item in the checklist snapshot:
   - Inspect physical or digital document submitted by applicant.
   - Click **Verify Item**.
   - Set Status: `RECEIVED`, `MISSING`, or `REJECTED`.
   - If `RECEIVED`: Enter mandatory **Evidence Reference ID** (e.g. `DOC-ID-99201`).
   - If `MISSING` or `REJECTED`: Enter mandatory **Audit Note** explaining the decision.
4. Click **Update Item**.

---

### 4. Compliance Admin Guide

#### Tasks & Responsibilities
- Conducting final review of loan cases.
- Approving, rejecting, or returning loan applications.

#### Step-by-Step Instructions

1. Navigate to **Loan Cases** -> **Pending Decision**.
2. Select a case where Risk Checker verification is complete.
3. Inspect checklist status.
   > [!WARNING]
   > The system will reject any `APPROVED` decision if any required checklist item is still `PENDING`, `MISSING`, or `REJECTED`.
4. Click **Make Decision**:
   - **APPROVED**: Final approval for disbursement.
   - **REJECTED**: Application declined.
   - **RETURNED**: Application sent back to HR/Applicant for revision.
   - **MORE_INFO**: Additional information required.
5. Enter a mandatory **Decision Reason**.
6. Submit decision. Audit event is permanently logged.

---

### 5. General Employee Guide

#### Tasks & Responsibilities
- Viewing personal payslips and deduction details.
- Contesting unauthorized payroll deductions.

#### Step-by-Step Instructions

##### A. Viewing Payslips & Deductions
1. Log in to the portal.
2. Navigate to **My Payroll** -> **Deductions**.
3. View itemized deductions (Statutory Tax, Pension, Custom Adjustments).

##### B. Contesting a Deduction
1. If an incorrect deduction appears on your payslip, click **Contest Deduction**.
2. Fill in the **Dispute Reason** detailing why the deduction is incorrect.
3. Click **Submit Contest**.
4. The deduction will enter `IS_HELD` status and will be frozen pending Finance review.

---

## 5. End-to-End Operational Workflows

### Workflow A: Monthly Payroll Cycle Execution

```mermaid
sequenceDiagram
    autonumber
    actor HR as HR Admin
    actor Fin as Finance User
    actor Emp as Employee
    participant Sys as Hr-Mastered API
    participant Worker as Delivery Worker

    HR->>Sys: 1. Create/Update Payroll Profiles (or CSV Import)
    HR->>Sys: 2. Initialize Draft Payroll Run (Month)
    HR->>Sys: 3. POST /api/payroll-runs/{uuid}/calculate/
    Note over Sys: Calculates Net Pay, applies Statutory Rules, caps deductions at max %
    Sys-->>HR: Run status: CALCULATED
    
    Emp->>Sys: 4. (Optional) Contest Deduction (POST .../contest/)
    Sys-->>Emp: Deduction flagged IS_HELD
    Fin->>Sys: 5. Resolve Contest (POST .../resolve/)

    Fin->>Sys: 6. POST /api/payroll-runs/{uuid}/review/
    Sys-->>Fin: Run status: REVIEWED
    
    Fin->>Sys: 7. POST /api/payroll-runs/{uuid}/approve/
    Sys-->>Fin: Run status: APPROVED
    
    Fin->>Sys: 8. POST /api/payroll-runs/{uuid}/export/
    Sys-->>Fin: Generates CSV/XLSX/PDF settlement pack + SHA256 checksums
    
    Fin->>Sys: 9. POST /api/payroll-runs/{uuid}/reconcile/
    Sys-->>Fin: Run status: RECONCILED / FAILED
    Sys->>Worker: 10. Enqueue delivery jobs (Email payslips / Zoho uploads)
```

---

### Workflow B: Loan Case Compliance & Approval Cycle

```mermaid
sequenceDiagram
    autonumber
    actor HR as HR Admin
    actor RC as Risk Checker
    actor CA as Compliance Admin
    participant Sys as Loan Compliance Engine

    HR->>Sys: 1. Create Loan Product & Checklist Template
    HR->>Sys: 2. POST /api/loan-cases/ (Create Case for Applicant)
    Note over Sys: Snapshots product checklist into LoanCaseChecklistItems
    Sys-->>HR: Case status: IN_REVIEW

    RC->>Sys: 3. POST /api/loan-cases/{uuid}/verify_checklist/
    Note over RC: Verifies evidence, enters evidence_reference or notes
    Sys-->>RC: Checklist item status: RECEIVED

    CA->>Sys: 4. POST /api/loan-cases/{uuid}/decide/
    alt All required checklist items RECEIVED
        Sys-->>CA: Decision: APPROVED (Case status: APPROVED)
    else Missing required evidence
        Sys-->>CA: 400 Bad Request: Missing evidence blocks compliance approval
    end
```
