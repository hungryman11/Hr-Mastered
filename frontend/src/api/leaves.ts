import client from './client';

export interface LeaveRequest {
  uuid: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED';
  leave_type: string;
  start_date: string;
  end_date: string;
  days_requested: number;
  reason: string;
  workdrive_url?: string;
  document_name?: string;
  created_at: string;
}

export interface LeaveBalance {
  leave_type_name: string;
  remaining_days: number;
  allocated_days: number; // assuming this exists or deriving from elsewhere
}

export interface LeaveApprovalStep {
  uuid: string;
  stage: 'ADMIN' | 'SUPERVISOR' | 'HOD' | 'HR';
  sequence: number;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  approver: string;
  decided_at: string | null;
  decision_reason: string | null;
}

export interface RoutingInfo {
  current_stage: string;
  current_approvers: string[];
  approval_steps: LeaveApprovalStep[];
}

export interface PendingLeaveApproval {
  uuid: string;
  employee_uuid: string;
  employee_id: number;
  employee_name: string;
  department: string | null;
  org_unit: string | null;
  position: string | null;
  leave_type: string;
  start_date: string;
  end_date: string;
  working_days: string;
  reason: string;
  supporting_document_name: string | null;
  supporting_document_url: string | null;
  status: string;
  current_approval_step: LeaveApprovalStep;
  approval_timeline: LeaveApprovalStep[];
  can_approve: boolean;
  can_reject: boolean;
}

export const getLeaveBalances = async (employeeUuid: string): Promise<LeaveBalance[]> => {
  const res = await client.get(`/leave-balances/?employee__uuid=${employeeUuid}`);
  return res.data;
};

export const createLeaveRequest = async (data: FormData): Promise<LeaveRequest> => {
  const res = await client.post('/leave-requests/', data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const getLeaveRequests = async (): Promise<LeaveRequest[]> => {
  const res = await client.get('/leave-requests/');
  return res.data;
};

export const getLeaveRequestDetail = async (uuid: string): Promise<LeaveRequest> => {
  const res = await client.get(`/leave-requests/${uuid}/`);
  return res.data;
};

export const getLeaveRequestRouting = async (uuid: string): Promise<RoutingInfo> => {
  const res = await client.get(`/leave-requests/${uuid}/routing/`);
  return res.data;
};

export const approveLeave = async (uuid: string, reason?: string) => {
  const res = await client.post(`/leave-requests/${uuid}/approve/`, { reason });
  return res.data;
};

export const rejectLeave = async (uuid: string, reason: string) => {
  const res = await client.post(`/leave-requests/${uuid}/reject/`, { reason });
  return res.data;
};

export const cancelLeave = async (uuid: string) => {
  const res = await client.post(`/leave-requests/${uuid}/cancel/`);
  return res.data;
};

export const getApprovalDecisions = async () => {
  const res = await client.get('/approval-decisions/');
  return res.data;
};

export const getPendingLeaveApprovals = async (): Promise<PendingLeaveApproval[]> => {
  const res = await client.get('/leave-requests/pending-approvals/');
  return res.data;
};
