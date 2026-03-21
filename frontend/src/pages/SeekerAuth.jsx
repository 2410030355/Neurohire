import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Brain, GraduationCap, ArrowLeft, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Link, useNavigate } from 'react-router-dom';
import { createPageUrl } from '@/utils';
import { API_BASE_URL, jsonFetch } from '@/api/http';
import ThemeToggle from '@/components/ui/ThemeToggle';

function GoogleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.35-8.16 2.35-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
    </svg>
  );
}

export default function SeekerAuth() {
  const navigate = useNavigate();
  const [mode, setMode] = useState('login');
  const [showEmail, setShowEmail] = useState(false);
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  // Check for Google error param on page load
  const urlParams = new URLSearchParams(window.location.search);
  const googleError = urlParams.get('error');

  // ✅ Real Google OAuth — redirects to Django social-auth
  const handleGoogle = () => {
    setGoogleLoading(true);
    // Django social-auth handles the full OAuth flow and redirects back to frontend
    window.location.href = `${API_BASE_URL}/api/auth/login/google-oauth2/`;
  };

  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email || !email.includes('@')) {
      setError('Please enter a valid email.');
      return;
    }
    // ✅ aligned with backend minimum of 8 characters
    if (!password || password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    setLoading(true);
    try {
      if (mode === 'signup') {
        const user = await jsonFetch('/api/auth/register/', {
          method: 'POST',
          body: JSON.stringify({
            email,
            password,
            full_name: fullName || email.split('@')[0],
            role: 'jobseeker',
          }),
        });
        if (user) localStorage.setItem('user', JSON.stringify(user));
      } else {
        const user = await jsonFetch('/api/auth/login/', {
          method: 'POST',
          body: JSON.stringify({ email, password }),
        });
        if (user) localStorage.setItem('user', JSON.stringify(user));
      }
      navigate(createPageUrl('SeekerDashboard'));
    } catch (err) {
      setError(err?.message || 'Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--nh-bg)' }}>
      {/* Nav */}
      <nav className="px-6 py-4 flex items-center justify-between">
        <Link to={createPageUrl('Home')} className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold" style={{ color: 'var(--nh-text)' }}>NEUROHIRE</span>
        </Link>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <Link to={createPageUrl('RoleSelect')}>
            <Button variant="ghost" className="rounded-xl" style={{ color: 'var(--nh-text-secondary)' }}>
              <ArrowLeft className="w-4 h-4 mr-1" /> Back
            </Button>
          </Link>
        </div>
      </nav>

      {/* Card */}
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          <div
            className="rounded-3xl p-8 shadow-2xl border"
            style={{ background: 'var(--nh-card)', borderColor: 'var(--nh-border)' }}
          >
            {/* Header */}
            <div className="flex items-center gap-3 mb-6">
              <div className="w-11 h-11 rounded-2xl flex items-center justify-center"
                style={{ background: 'var(--nh-primary-light)' }}>
                <GraduationCap className="w-6 h-6" style={{ color: 'var(--nh-primary)' }} />
              </div>
              <div>
                <h1 className="text-xl font-bold" style={{ color: 'var(--nh-text)' }}>
                  {mode === 'login' ? 'Job Seeker Login' : 'Create Seeker Account'}
                </h1>
                <p className="text-xs" style={{ color: 'var(--nh-text-secondary)' }}>
                  Find your next opportunity
                </p>
              </div>
            </div>

            {/* Google error */}
            {googleError && (
              <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm mb-4">
                <AlertCircle className="w-4 h-4 shrink-0" />
                Google sign-in failed. Please try email instead.
              </div>
            )}

            {/* Google Button */}
            <button
              onClick={handleGoogle}
              disabled={googleLoading}
              className="w-full flex items-center justify-center gap-3 h-11 rounded-xl border font-medium text-sm transition-all hover:shadow-md active:scale-[0.98]"
              style={{ borderColor: 'var(--nh-border)', color: 'var(--nh-text)', background: 'var(--nh-card)' }}
            >
              {googleLoading
                ? <span className="animate-spin w-5 h-5 border-2 border-slate-300 border-t-blue-500 rounded-full" />
                : <GoogleIcon />}
              {googleLoading ? 'Redirecting to Google…' : 'Continue with Google'}
            </button>

            {/* Divider */}
            <div className="flex items-center gap-3 my-5">
              <div className="flex-1 h-px" style={{ background: 'var(--nh-border)' }} />
              <span className="text-xs font-medium" style={{ color: 'var(--nh-text-secondary)' }}>
                or continue with email
              </span>
              <div className="flex-1 h-px" style={{ background: 'var(--nh-border)' }} />
            </div>

            {/* Email toggle */}
            {!showEmail ? (
              <button
                onClick={() => setShowEmail(true)}
                className="w-full h-11 rounded-xl border text-sm font-medium transition-all hover:shadow-sm"
                style={{ borderColor: 'var(--nh-border)', color: 'var(--nh-text-secondary)', background: 'transparent' }}
              >
                Use email instead
              </button>
            ) : (
              <motion.form
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                onSubmit={handleEmailSubmit}
                className="space-y-4"
              >
                {/* Full name — signup only */}
                {mode === 'signup' && (
                  <div>
                    <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--nh-text)' }}>
                      Full Name
                    </label>
                    <Input
                      type="text"
                      placeholder="Your name"
                      value={fullName}
                      onChange={e => setFullName(e.target.value)}
                      className="rounded-xl"
                    />
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--nh-text)' }}>
                    Email
                  </label>
                  <Input
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={e => { setEmail(e.target.value); setError(''); }}
                    className="rounded-xl"
                    autoComplete="email"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--nh-text)' }}>
                    Password
                  </label>
                  <div className="relative">
                    <Input
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Min. 8 characters"
                      value={password}
                      onChange={e => { setPassword(e.target.value); setError(''); }}
                      className="rounded-xl pr-10"
                      autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(v => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2"
                      style={{ color: 'var(--nh-text-secondary)' }}
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  {mode === 'signup' && password.length > 0 && password.length < 8 && (
                    <p className="mt-1 text-xs text-amber-500">
                      {8 - password.length} more character{8 - password.length !== 1 ? 's' : ''} needed
                    </p>
                  )}
                </div>

                {error && (
                  <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm">
                    <AlertCircle className="w-4 h-4 shrink-0" /> {error}
                  </div>
                )}

                <Button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-xl h-11 font-semibold text-white border-0 gradient-bg"
                >
                  {loading ? 'Please wait…' : mode === 'login' ? 'Sign In' : 'Create Account'}
                </Button>
              </motion.form>
            )}

            {/* Mode switch */}
            <div className="mt-5 text-center text-sm" style={{ color: 'var(--nh-text-secondary)' }}>
              {mode === 'login' ? (
                <>Don't have an account?{' '}
                  <button
                    onClick={() => { setMode('signup'); setError(''); setShowEmail(false); }}
                    className="font-semibold" style={{ color: 'var(--nh-primary)' }}
                  >
                    Sign up
                  </button>
                </>
              ) : (
                <>Already have an account?{' '}
                  <button
                    onClick={() => { setMode('login'); setError(''); setShowEmail(false); }}
                    className="font-semibold" style={{ color: 'var(--nh-primary)' }}
                  >
                    Sign in
                  </button>
                </>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}