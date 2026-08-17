import client from './client';

export interface DeliveryJob {
  uuid: string;
  kind: string;
  status: 'PENDING' | 'PROCESSING' | 'SUCCEEDED' | 'FAILED';
  attempts: number;
  last_error: string | null;
  created_at: string;
}

export const getDeliveryJobs = async (): Promise<DeliveryJob[]> => {
  const res = await client.get('/delivery-jobs/');
  return res.data;
};

export const retryDeliveryJob = async (uuid: string) => {
  const res = await client.post(`/delivery-jobs/${uuid}/retry/`);
  return res.data;
};
