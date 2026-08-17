import { useState } from 'react';
import { getLoginUrl, getOAuthRedirectUri } from '../api/auth';
import styles from './Login.module.css';
import { useToast } from '../contexts/ToastContext';
import LoadingSpinner from '../components/LoadingSpinner';

const Login = () => {
  const [loading, setLoading] = useState(false);
  const { addToast } = useToast();

  const handleLogin = async () => {
    setLoading(true);

    try {
      // Zoho must redirect the browser back into this SPA (OAuthCallback, at
      // /app/callback), not straight at the Django API - otherwise the user
      // lands on a bare JSON response instead of the app. This value must be
      // registered in the Zoho API Console and listed in the backend's
      // ZOHO_ALLOWED_REDIRECT_URIS.
      const redirectUri = getOAuthRedirectUri();

      const data = await getLoginUrl(redirectUri);

      if (!data.login_url) {
        throw new Error('Backend did not return a login URL.');
      }

      // Redirect the browser to Zoho.
      window.location.assign(data.login_url);
    } catch (error) {
      console.error(error);
      addToast('Failed to initialise login.', 'error');
      setLoading(false);
    }
  };

  return (
    <div className={styles.loginContainer}>
      <div className={styles.animatedBg}></div>

      <div className={`card ${styles.loginCard}`}>
        <div className={styles.logo}>
          <div className={styles.logoIcon}>HR</div>
          <h1>HR Mastered</h1>
        </div>

        <p className={styles.subtitle}>
          Sign in to access your employee portal
        </p>

        {loading ? (
          <LoadingSpinner />
        ) : (
          <button
            className={styles.zohoBtn}
            onClick={handleLogin}
          >
            <svg
              className={styles.zohoIcon}
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M2.5 19.5L10 6H4V4H19V6L11.5 19.5H18V21.5H3V19.5H2.5Z" />
            </svg>

            Sign in with Zoho Mail
          </button>
        )}
      </div>
    </div>
  );
};

export default Login;