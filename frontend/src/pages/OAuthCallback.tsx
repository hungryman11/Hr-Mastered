import { useEffect, useRef } from 'react';
import axios from 'axios';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { handleCallback, getOAuthRedirectUri } from '../api/auth';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import LoadingSpinner from '../components/LoadingSpinner';

const OAuthCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const { addToast } = useToast();
  const exchangeStarted = useRef(false);

  useEffect(() => {
    // React Strict Mode re-runs effects in development. Django consumes the
    // session-bound OAuth state after the first relay request, so never relay
    // the same authorization code/state pair twice from this mounted callback.
    if (exchangeStarted.current) return;
    exchangeStarted.current = true;

    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const zohoError = searchParams.get('error');
    const zohoErrorDescription = searchParams.get('error_description');

    // Temporary callback diagnostics. Values that could be credentials are
    // redacted; only parameter names and boolean presence flags are recorded.
    const redactedCallbackUrl = new URL(window.location.href);
    redactedCallbackUrl.searchParams.delete('code');
    redactedCallbackUrl.searchParams.delete('state');
    console.info('Zoho OAuth callback diagnostics', {
      href: redactedCallbackUrl.toString(),
      pathname: window.location.pathname,
      searchParameterNames: Array.from(searchParams.keys()),
      codePresent: Boolean(code),
      statePresent: Boolean(state),
      errorPresent: Boolean(zohoError),
      errorDescription: zohoErrorDescription || undefined,
    });
    
    if (code && state) {
      // Must be the exact same redirect_uri that was sent to /zoho/auth/login-url/,
      // since the backend validates the callback's redirect_uri against the one
      // stored for this login attempt.
      const redirectUri = getOAuthRedirectUri();
      handleCallback(code, state, redirectUri)
        .then(async () => {
          await refreshUser();
          navigate('/app/dashboard');
        })
        .catch((error: unknown) => {
          const diagnostic = axios.isAxiosError(error) ? error.response?.data : undefined;
          const detail = diagnostic?.detail;
          const stage = diagnostic?.stage;
          const errorType = diagnostic?.error_type;
          const safeError = diagnostic?.error;
          const diagnosticMessage = stage && errorType && safeError
            ? `${detail} [${stage}: ${errorType}: ${safeError}]`
            : detail;
          addToast(diagnosticMessage || 'Login failed', 'error');
          navigate('/app/login');
        });
    } else {
      addToast(
        zohoError
          ? `Zoho OAuth error: ${zohoErrorDescription || zohoError}`
          : 'Invalid callback params',
        'error'
      );
      navigate('/app/login');
    }
  }, [searchParams, navigate, refreshUser, addToast]);

  return (
    <div style={{ height: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
      <LoadingSpinner />
      <p style={{ marginLeft: '1rem' }}>Authenticating...</p>
    </div>
  );
};

export default OAuthCallback;
