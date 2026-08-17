import client from './client';

export interface KpiTemplate {
  uuid: string;
  name: string;
  category: string | null;
  measurement_type: string;
  default_target: string | null;
  default_weight: number;
}

export interface KpiFramework {
  uuid: string;
  name: string;
  scope_type: string;
  configuration: any;
  position?: string;
  org_unit?: string | null;
}

export interface PerformanceCycle {
  uuid: string;
  name: string;
  start_date: string;
  end_date: string;
  locked?: boolean;
}

export interface KpiAssignment {
  uuid: string;
  employee: any;
  template: KpiTemplate;
  target: string | null;
  weight: number;
}

export const getKpiTemplates = async (): Promise<KpiTemplate[]> => {
  const res = await client.get('/kpi-templates/');
  return res.data;
};

export const getKpiTemplate = async (uuid: string): Promise<KpiTemplate> => {
  const res = await client.get(`/kpi-templates/${uuid}/`);
  return res.data;
};

export const createKpiTemplate = async (payload: Partial<KpiTemplate>): Promise<KpiTemplate> => {
  const res = await client.post('/kpi-templates/', payload);
  return res.data;
};

export const updateKpiTemplate = async (uuid: string, payload: Partial<KpiTemplate>): Promise<KpiTemplate> => {
  const res = await client.put(`/kpi-templates/${uuid}/`, payload);
  return res.data;
};

export const getKpiFrameworks = async (): Promise<KpiFramework[]> => {
  const res = await client.get('/kpi-frameworks/');
  return res.data;
};

export const getKpiFramework = async (uuid: string): Promise<KpiFramework> => {
  const res = await client.get(`/kpi-frameworks/${uuid}/`);
  return res.data;
};

export const createKpiFramework = async (payload: Partial<KpiFramework>): Promise<KpiFramework> => {
  const res = await client.post('/kpi-frameworks/', payload);
  return res.data;
};

export const updateKpiFramework = async (uuid: string, payload: Partial<KpiFramework>): Promise<KpiFramework> => {
  const res = await client.put(`/kpi-frameworks/${uuid}/`, payload);
  return res.data;
};

export const getPerformanceCycles = async (): Promise<PerformanceCycle[]> => {
  const res = await client.get('/performance-cycles/');
  return res.data;
};

export const updatePerformanceCycle = async (uuid: string, payload: Partial<PerformanceCycle>): Promise<PerformanceCycle> => {
  const res = await client.put(`/performance-cycles/${uuid}/`, payload);
  return res.data;
};

export const generateAssignments = async (cycleUuid: string): Promise<KpiAssignment[]> => {
  const res = await client.post(`/performance-cycles/${cycleUuid}/generate_assignments/`);
  return res.data;
};

export const getKpiAssignments = async (): Promise<KpiAssignment[]> => {
  const res = await client.get('/kpi-assignments/');
  return res.data;
};

export default {};
