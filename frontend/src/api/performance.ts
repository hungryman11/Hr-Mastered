import client from './client';

export interface PerformanceReview {
  uuid: string;
  cycle: string;
  cycle_name: string;
  employee: number;
  employee_name: string;
  department_name: string;
  position_title: string;
  system_score: string;
  employee_self_score: string | null;
  employee_comments: string;
  manager_score: string | null;
  manager_comments: string;
  hr_score: string | null;
  hr_comments: string;
  calibrated_score: string | null;
  final_score: string | null;
  final_comments: string;
  status: 'DRAFT' | 'SUBMITTED' | 'MANAGER_REVIEWED' | 'HR_REVIEWED' | 'CALIBRATED' | 'FINALIZED';
}

const unwrap = <T>(data: T[] | { results?: T[] }): T[] => Array.isArray(data) ? data : data.results ?? [];
export const getPerformanceReviews = async (): Promise<PerformanceReview[]> => unwrap((await client.get('/performance-reviews/')).data);
export const getPerformanceReview = async (uuid: string): Promise<PerformanceReview> => (await client.get(`/performance-reviews/${uuid}/`)).data;
export const performReviewAction = async (uuid: string, action: 'self_assessment' | 'manager_review' | 'hr_review' | 'calibrate' | 'finalize', payload: Record<string, string>) => (await client.post(`/performance-reviews/${uuid}/${action}/`, payload)).data as PerformanceReview;
