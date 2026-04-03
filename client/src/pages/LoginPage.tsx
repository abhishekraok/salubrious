import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../contexts/AuthContext';

export function LoginPage() {
  const { login } = useAuth();

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center space-y-6">
        <h1 className="text-3xl font-semibold tracking-tight">Salubrious</h1>
        <p className="text-calm-muted text-sm">Sign in to manage your portfolio</p>
        <div className="flex justify-center">
          <GoogleLogin
            onSuccess={(response) => {
              if (response.credential) {
                login(response.credential);
              }
            }}
            onError={() => {
              console.error('Google login failed');
            }}
          />
        </div>
      </div>
    </div>
  );
}
