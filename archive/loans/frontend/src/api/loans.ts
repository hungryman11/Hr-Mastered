import client from './client';

export interface LoanProduct {
  uuid: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoanChecklistItem {
  uuid: string;
  loan_case: string;
  name: string;
  required: boolean;
  status: string;
  evidence_reference: string;
  note: string;
  checked_by: number | null;
  checked_at: string | null;
}

export interface LoanCase {
  uuid: string;
  applicant: number;
  applicant_name: string;
  loan_product: string;
  product_name: string;
  requested_amount: string;
  purpose: string;
  repayment_months: number;
  collateral_type: string;
  collateral_value: string;
  collateral_details: string;
  assigned_checker: number | null;
  status: string;
  recommendation: string;
  decision_reason: string;
  checklist_items: LoanChecklistItem[];
  created_at: string;
  updated_at: string;
}

export interface CreateLoanCasePayload {
  applicant: number | string;
  loan_product: string;
  requested_amount: string;
  purpose: string;
  repayment_months: number;
  collateral_type: string;
  collateral_value: string;
  collateral_details: string;
}

const unwrap = <T>(data: { results?: T[] } | T[]): T[] =>
  Array.isArray(data) ? data : data.results ?? [];

export const getLoanProducts = async (): Promise<LoanProduct[]> => {
  const res = await client.get('/loan-products/');
  return unwrap(res.data);
};

export const getLoanCases = async (): Promise<LoanCase[]> => {
  const res = await client.get('/loan-cases/');
  return unwrap(res.data);
};

export const getLoanCase = async (uuid: string): Promise<LoanCase> => {
  const res = await client.get(`/loan-cases/${uuid}/`);
  return res.data;
};

export const createLoanCase = async (payload: CreateLoanCasePayload): Promise<LoanCase> => {
  const res = await client.post('/loan-cases/', payload);
  return res.data;
};

export const verifyChecklistItem = async (
  caseUuid: string,
  itemUuid: string,
  status: string,
  note: string,
  evidenceReference: string
): Promise<LoanChecklistItem> => {
  const res = await client.post(`/loan-cases/${caseUuid}/verify_checklist/`, {
    item_uuid: itemUuid,
    status,
    note,
    evidence_reference: evidenceReference,
  });
  return res.data;
};

export const decideLoanCase = async (caseUuid: string, decision: string, reason: string): Promise<LoanCase> => {
  const res = await client.post(`/loan-cases/${caseUuid}/decide/`, { decision, reason });
  return res.data;
};
