import client from './client';

export type UserRole =
  | 'EMPLOYEE'
  | 'MANAGER'
  | 'HOD'
  | 'HR_ADMIN'
  | 'FINANCE'
  | 'ADMIN'
  | 'SUPERVISOR';


export interface User {
  id: number;
  uuid: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  company_name?: string;
}

export const getLoginUrl = async (redirectUri: string) => {
  const res = await client.get(`/zoho/auth/login-url/?redirect_uri=${encodeURIComponent(redirectUri)}`);
  return res.data;
};

export const LOCAL_OAUTH_REDIRECT_URI = 'http://localhost:5173/app/callback';

// Zoho and Django compare redirect URIs exactly. Local development is deliberately
// pinned to localhost so a browser opened at 127.0.0.1 cannot create a session on
// one origin and receive the OAuth callback on another.
export const getOAuthRedirectUri = (): string => {
  if (import.meta.env.DEV) {
    if (window.location.origin !== 'http://localhost:5173') {
      throw new Error('Local Zoho OAuth must be started at http://localhost:5173.');
    }
    return LOCAL_OAUTH_REDIRECT_URI;
  }

  return `${window.location.origin}/app/callback`;
};

export const handleCallback = async (code: string, state: string, redirectUri: string) => {
  const res = await client.get(
    `/zoho/auth/callback/?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}&redirect_uri=${encodeURIComponent(redirectUri)}`
  );
  return res.data;
};

export const getCurrentUser = async (): Promise<User> => {
  const res = await client.get('/employees/me/');
  return res.data;
};
