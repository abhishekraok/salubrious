import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';

export function LoginPage() {
  const { authConfig, login, register, loginWithGoogle } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (isRegister) {
        await register(name, email, password);
      } else {
        await login(email, password);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    if (!authConfig?.google_client_id) return;

    // Use Google Identity Services
    const google = (window as any).google;
    if (!google?.accounts?.id) {
      setError('Google Sign-In not loaded. Please refresh the page.');
      return;
    }

    google.accounts.id.initialize({
      client_id: authConfig.google_client_id,
      callback: async (response: any) => {
        setLoading(true);
        setError('');
        try {
          await loginWithGoogle(response.credential);
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Google login failed');
        } finally {
          setLoading(false);
        }
      },
    });

    google.accounts.id.prompt();
  };

  return (
    <div className="min-h-screen bg-calm-bg flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-semibold text-calm-text text-center mb-2">Salubrious</h1>
        <p className="text-calm-muted text-center text-sm mb-6">Calm portfolio tracking</p>

        <Card>
          <div className="p-6">
            {authConfig?.oauth_enabled ? (
              <div className="space-y-4">
                <Button onClick={handleGoogleLogin} disabled={loading} className="w-full">
                  Sign in with Google
                </Button>
                {error && <p className="text-calm-red text-sm">{error}</p>}
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <h2 className="text-lg font-medium text-calm-text">
                  {isRegister ? 'Create account' : 'Sign in'}
                </h2>

                {isRegister && (
                  <div>
                    <label className="block text-sm text-calm-muted mb-1">Name</label>
                    <input
                      type="text"
                      value={name}
                      onChange={e => setName(e.target.value)}
                      required
                      className="w-full px-3 py-2 border border-calm-border rounded-md bg-calm-surface text-calm-text focus:outline-none focus:border-calm-blue"
                    />
                  </div>
                )}

                <div>
                  <label className="block text-sm text-calm-muted mb-1">Email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    required
                    className="w-full px-3 py-2 border border-calm-border rounded-md bg-calm-surface text-calm-text focus:outline-none focus:border-calm-blue"
                  />
                </div>

                <div>
                  <label className="block text-sm text-calm-muted mb-1">Password</label>
                  <input
                    type="password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                    minLength={6}
                    className="w-full px-3 py-2 border border-calm-border rounded-md bg-calm-surface text-calm-text focus:outline-none focus:border-calm-blue"
                  />
                </div>

                {error && <p className="text-calm-red text-sm">{error}</p>}

                <Button type="submit" disabled={loading} className="w-full">
                  {loading ? 'Please wait...' : isRegister ? 'Create account' : 'Sign in'}
                </Button>

                <p className="text-center text-sm text-calm-muted">
                  {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
                  <button
                    type="button"
                    onClick={() => { setIsRegister(!isRegister); setError(''); }}
                    className="text-calm-blue underline"
                  >
                    {isRegister ? 'Sign in' : 'Create one'}
                  </button>
                </p>
              </form>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
