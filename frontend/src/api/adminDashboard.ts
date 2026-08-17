import client from './client';

export interface DashboardSummary {
  total_active_employees: number;
  total_inactive_employees: number;
  employees_by_role: Record<string, number>;
  pending_onboarding: number;
  departments: number;
  org_units: number;
  positions: number;
  pending_leave_requests: number;
  payroll_runs_in_progress: number;
}

export interface RecentEmployee {
  id: number;
  uuid: string;
  first_name: string;
  last_name: string;
  email: string;
  role: string;
  onboarding_status: string;
  created_at: string;
}

export interface DepartmentStats {
  department_id: number;
  department_name: string;
  active_count: number;
  inactive_count: number;
  total: number;
}

export interface OrgStructure {
  org_units: Array<{ id: number; name: string; type: string; employee_count: number }>;
  positions: Array<{ id: number; title: string; org_unit_id: number | null; employee_count: number }>;
}

export const getDashboardSummary = async (): Promise<DashboardSummary> => {
  const res = await client.get('/admin-dashboard/summary/');
  return res.data;
};

export const getRecentEmployees = async (): Promise<RecentEmployee[]> => {
  const res = await client.get('/admin-dashboard/recent_employees/');
  return res.data;
};

export const getEmployeeStats = async (): Promise<DepartmentStats[]> => {
  const res = await client.get('/admin-dashboard/employee_stats/');
  return res.data;
};

export const getOrgStructure = async (): Promise<OrgStructure> => {
  const res = await client.get('/admin-dashboard/organization_structure/');
  return res.data;
};
