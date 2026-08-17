import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import styles from './Login.module.css';

type DemoUser = { username: string; role: string };
type DemoLoginUsersResponse = { users: DemoUser[]; csrf_token: string };

const DemoLogin = () => {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [users, setUsers] = useState<DemoUser[]>([]);
  const [csrfToken, setCsrfToken] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    client.get<DemoLoginUsersResponse>('/demo-auth/users/').then((response) => {
      setUsers(response.data.users || []);
      setCsrfToken(response.data.csrf_token || '');
    }).catch(() => setError('Demo login is available only in DEBUG with seeded demo data.'));
  }, []);

  const login = async (username: string) => {
    setError('');
    try {
      await client.post('/demo-auth/login/', JSON.stringify({ username }), {
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      });
      // Confirm the rotated Django session cookie is usable and populate the
      // shared auth context before a protected route renders.
      await refreshUser();
      navigate('/app/dashboard');
    } catch (error) {
      const status = axios.isAxiosError(error) ? error.response?.status : undefined;
      setError(status
        ? `Demo login could not be completed (HTTP ${status}).`
        : 'Could not create the local demo session. Check that both local servers are running.');
    }
  };

  return <div className={styles.loginContainer}><div className="card"><h1>UAT demo login</h1><p>Select a seeded local role. This page is disabled outside DEBUG.</p>
    {error && <p role="alert">{error}</p>}
    {users.map((user) => <button className={styles.zohoBtn} key={user.username} onClick={() => login(user.username)}>{user.username} — {user.role}</button>)}
  </div></div>;
};

export default DemoLogin;
