import client from './client';

export interface LeaveType {
  uuid: string;
  name: string;
  default_days: number;
  max_days_per_request: number;
  requires_supporting_document: boolean;
  carry_over_days: number;
}

export const getLeaveTypes = async (): Promise<LeaveType[]> => {
  const res = await client.get('/leave-types/');
  return res.data;
};

export const createLeaveType = async (data: Partial<LeaveType>): Promise<LeaveType> => {
  const res = await client.post('/leave-types/', data);
  return res.data;
};

export const updateLeaveType = async (uuid: string, data: Partial<LeaveType>): Promise<LeaveType> => {
  const res = await client.put(`/leave-types/${uuid}/`, data);
  return res.data;
};
