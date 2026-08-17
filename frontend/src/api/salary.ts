import client from './client';

export interface SalaryRecord {
  uuid: string;
  employee: number;
  employee_name: string;
  employee_username: string;
  effective_date: string;
  end_date: string | null;
  currency: string;
  base_salary: string;
  housing_allowance: string;
  transport_allowance: string;
  meal_allowance: string;
  other_allowances: string;
  gross_salary: string;
  reason: string;
  status: string;
  status_display: string;
}

export type SalaryPayload = Omit<SalaryRecord, 'uuid' | 'employee_name' | 'employee_username' | 'gross_salary' | 'status_display'>;

export const getCurrentSalary = async (): Promise<SalaryRecord> => (await client.get('/salary-records/current/')).data;
export const getSalaryRecords = async (): Promise<SalaryRecord[]> => (await client.get('/salary-records/')).data;
export const createSalaryRecord = async (payload: Partial<SalaryPayload>): Promise<SalaryRecord> => (await client.post('/salary-records/', payload)).data;
export const supersedeSalaryRecord = async (payload: Record<string, string | number>): Promise<SalaryRecord> => (await client.post('/salary-records/supersede/', payload)).data;
