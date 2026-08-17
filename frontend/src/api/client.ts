import axios from 'axios';

const client = axios.create({
  baseURL: '/api/',
  withCredentials: true,
});

// Helper to get cookie by name
function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(';').shift() || null;
  return null;
}

client.interceptors.request.use((config) => {
  if (config.method && ['post', 'put', 'patch', 'delete'].includes(config.method)) {
    // Only set X-CSRFToken if not already explicitly provided by caller.
    // DemoLogin and other endpoints may provide an explicit token.
    if (!config.headers['X-CSRFToken']) {
      const csrfToken = getCookie('csrftoken');
      if (csrfToken) {
        config.headers['X-CSRFToken'] = csrfToken;
      }
    }
  }
  return config;
});

export default client;
