import client from './client';

export interface PayrollProfile {
  uuid: string;
  employee: number;
  employee_number: string;
  base_salary: string;
  bank_code: string;
  employment_status: string;
  hire_date: string;
}

export interface ReconciliationRecord {
  uuid: string;
  bank_reference: string;
  result: 'SUCCESS' | 'FAILED';
  details: Record<string, unknown>;
  reconciled_by: number | null;
  created_at: string;
}

export interface PayrollRun {
  uuid: string;
  month: string;
  status: string;
  total_gross: string;
  total_deductions: string;
  total_held: string;
  net_payroll: string;
  calculated_by: number | null;
  approved_by: number | null;
  approved_at: string | null;
  created_at: string;
  reconciliation?: ReconciliationRecord | null;
}

export interface PayrollDeduction {
  uuid: string;
  kind: string;
  name: string;
  amount: string;
  reason: string;
  is_held: boolean;
  contested_at: string | null;
  contest_reason: string;
  resolution_notes: string;
  employee_name: string;
  employee_uuid: string;
  payroll_run_uuid: string;
  payroll_month: string;
}

export interface CsvValidationError {
  line_number: number;
  row: Record<string, string>;
  issues: string[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

const unwrap = <T>(data: PaginatedResponse<T> | T[]): T[] =>
  Array.isArray(data) ? data : data.results ?? [];

export const getPayrollProfiles = async (): Promise<PayrollProfile[]> => {
  const res = await client.get('/payroll-profiles/');
  return unwrap(res.data);
};

export interface CsvValidationResult {
  valid_rows: number;
  errors: CsvValidationError[];
}

export const validatePayrollProfilesCsv = async (file: File): Promise<CsvValidationResult> => {
  const form = new FormData();
  form.append('file', file);
  const res = await client.post('/payroll-profiles/validate_csv/', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const importPayrollProfiles = async (file: File) => {
  const form = new FormData();
  form.append('file', file);
  const res = await client.post('/payroll-profiles/import_csv/', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data as { imported_profiles: number };
};

export const parsePayrollImportError = (err: unknown): CsvValidationError[] | string => {
  if (typeof err === 'object' && err !== null && 'response' in err) {
    const data = (err as { response?: { data?: unknown } }).response?.data;
    if (data && typeof data === 'object' && 'rows' in data && Array.isArray((data as { rows: unknown }).rows)) {
      return (data as { rows: CsvValidationError[] }).rows;
    }
    if (data && typeof data === 'object' && 'detail' in data) {
      return String((data as { detail: unknown }).detail);
    }
  }
  return 'Import failed.';
};

export const getPayrollRuns = async (): Promise<PayrollRun[]> => {
  const res = await client.get('/payroll-runs/');
  return unwrap(res.data);
};

export const getPayrollRun = async (uuid: string): Promise<PayrollRun> => {
  const res = await client.get(`/payroll-runs/${uuid}/`);
  return res.data;
};

export const createPayrollRun = async (month: string): Promise<PayrollRun> => {
  const res = await client.post('/payroll-runs/', { month });
  return res.data;
};

export const calculatePayrollRun = async (uuid: string): Promise<PayrollRun> => {
  const res = await client.post(`/payroll-runs/${uuid}/calculate/`);
  return res.data;
};

export const reviewPayrollRun = async (uuid: string): Promise<PayrollRun> => {
  const res = await client.post(`/payroll-runs/${uuid}/review/`);
  return res.data;
};

export const approvePayrollRun = async (uuid: string): Promise<PayrollRun> => {
  const res = await client.post(`/payroll-runs/${uuid}/approve/`);
  return res.data;
};

export const exportPayrollRun = async (uuid: string, format = 'PACK'): Promise<{ file_paths: string[] }> => {
  const res = await client.post(`/payroll-runs/${uuid}/export/`, { format });
  return res.data;
};

export const reconcilePayrollRun = async (
  uuid: string,
  bankReference: string,
  result: 'SUCCESS' | 'FAILED',
  details: Record<string, unknown> = {}
): Promise<PayrollRun> => {
  const res = await client.post(`/payroll-runs/${uuid}/reconcile/`, {
    bank_reference: bankReference,
    result,
    details,
  });
  return res.data;
};

export const getPayrollDeductions = async (): Promise<PayrollDeduction[]> => {
  const res = await client.get('/payroll-deductions/');
  return unwrap(res.data);
};

export const contestDeduction = async (uuid: string, reason: string) => {
  const res = await client.post(`/payroll-deductions/${uuid}/contest/`, { reason });
  return res.data;
};

export const resolveDeduction = async (uuid: string, uphold: boolean, notes: string) => {
  const res = await client.post(`/payroll-deductions/${uuid}/resolve/`, { uphold, notes });
  return res.data;
};
