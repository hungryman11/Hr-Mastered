import client from './client';

export interface EmployeeOption {
  id: number;
  uuid: string;
  first_name: string;
  last_name: string;
  username: string;
  email?: string | null;
  role?: string | null;
  department_name?: string | null;
  org_unit_name?: string | null;
  is_active?: boolean;
}

const unwrap = <T>(data: T[] | { results?: T[] }): T[] => Array.isArray(data) ? data : data.results ?? [];

/** The backend scopes this list to the authenticated HR user's company. */
export const getEmployees = async (): Promise<EmployeeOption[]> => unwrap((await client.get('/employees/')).data);

export const employeeLabel = (employee: EmployeeOption) => {
  const name = `${employee.first_name} ${employee.last_name}`.trim() || employee.username;
  return `${name} · ${employee.org_unit_name || employee.department_name || 'No org unit'}`;
};
