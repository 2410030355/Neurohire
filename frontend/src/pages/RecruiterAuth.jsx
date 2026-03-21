import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Eye, EyeOff, Brain, Mail, Lock, User, Building } from 'lucide-react';
import { jsonFetch } from '@/api/http';
import { createPageUrl } from '@/utils';
import { useNavigate } from 'react-router-dom';

const GOOGLE_OAUTH_URL = '/auth/login/google-oauth2/';

export default function RecruiterAuth() {
  const [tab, setTab]         = useState('login');   // 'login' | 'register'
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState('');
  const navigate = useNavigate();

  const [form, setForm] = useState({
    email: '', password: '', full_name: '', company: '',
  });

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async () => {
    setError('');
    setLoading(true);
    try {
      const endpoint = tab === 'login' ? '/api/auth/login/' : '/api/auth/register/';
      const body = tab === 'login'
        ? { email: form.email, password: form.password }
        : { email: form.email, password: form.password, full_name: form.full_name, role: 'recruiter' };

      const data = await jsonFetch(endpoint, { method: 'POST', body: JSON.stringify(body) });

      if (data?.error) { setError(data.error); return; }
      if (data?.user) localStorage.setItem('user', JSON.stringify(data.user));
      navigate(createPageUrl('RecruiterDashboard'));
    } catch (e) {
      setError(e.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  const googleUser = (() => {
    try {
      const raw = document.cookie.split(';').find(c => c.trim().startsWith('google_hint='));
      return raw ? decodeURIComponent(raw.split('=')[1]) : null;
    } catch { return null; }
  })();

  return (
    <div className="auth-bg min-h-screen flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-sm"
      >
        {/* ── Card ── */}
        <div className="rounded-3xl overflow-hidden"
          style={{
            background: 'var(--nh-card)',
            border: '1px solid var(--nh-border)',
            boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
          }}>

          {/* ── Logo header ── */}
          <div className="pt-8 pb-4 px-8 flex flex-col items-center">
            <div className="w-16 h-16 rounded-2xl gradient-bg flex items-center justify-center shadow-lg mb-3">
              <Brain className="w-9 h-9 text-white" />
            </div>
            <h1 className="text-xl font-bold tracking-widest gradient-text">NEUROHIRE</h1>
            <p className="text-xs mt-1 font-medium tracking-widest uppercase"
              style={{ color: 'var(--nh-text-secondary)' }}>
              AI Recruitment Engine
            </p>
          </div>

          {/* ── Tabs ── */}
          <div className="px-6 pb-2">
            <div className="flex rounded-xl p-1" style={{ background: 'var(--nh-bg)' }}>
              {['login', 'register'].map(t => (
                <button key={t} onClick={() => { setTab(t); setError(''); }}
                  className="flex-1 py-2 rounded-lg text-sm font-semibold transition-all capitalize"
                  style={{
                    background: tab === t ? 'linear-gradient(135deg, var(--nh-grad-from), var(--nh-grad-to))' : 'transparent',
                    color: tab === t ? '#fff' : 'var(--nh-text-secondary)',
                    boxShadow: tab === t ? '0 2px 8px rgba(45,212,191,0.25)' : 'none',
                  }}>
                  {t === 'login' ? 'Log In' : 'Sign Up'}
                </button>
              ))}
            </div>
          </div>

          {/* ── Form ── */}
          <div className="px-6 pb-6 pt-4 space-y-3">

            <AnimatePresence mode="wait">
              {tab === 'register' && (
                <motion.div key="name"
                  initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.2 }}>
                  <InputField icon={User} placeholder="Full name"
                    value={form.full_name} onChange={set('full_name')} />
                </motion.div>
              )}
            </AnimatePresence>

            <InputField icon={Mail} placeholder="you@company.com" type="email"
              value={form.email} onChange={set('email')} />

            <div className="relative">
              <InputField icon={Lock} placeholder="Password"
                type={showPass ? 'text' : 'password'}
                value={form.password} onChange={set('password')} />
              <button onClick={() => setShowPass(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 opacity-50 hover:opacity-100 transition-opacity">
                {showPass
                  ? <EyeOff className="w-4 h-4" style={{ color: 'var(--nh-text-secondary)' }} />
                  : <Eye    className="w-4 h-4" style={{ color: 'var(--nh-text-secondary)' }} />
                }
              </button>
            </div>

            {/* Error */}
            <AnimatePresence>
              {error && (
                <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                  className="text-xs px-3 py-2 rounded-xl"
                  style={{ background: 'rgba(248,113,113,0.1)', color: 'var(--nh-danger)' }}>
                  {error}
                </motion.p>
              )}
            </AnimatePresence>

            {/* Submit */}
            <motion.button
              whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              onClick={handleSubmit} disabled={loading}
              className="w-full py-3 rounded-xl font-semibold text-white text-sm transition-all mt-1"
              style={{
                background: 'linear-gradient(135deg, var(--nh-grad-from), var(--nh-grad-to))',
                opacity: loading ? 0.7 : 1,
                boxShadow: '0 4px 16px rgba(45,212,191,0.3)',
              }}>
              {loading ? 'Please wait…' : tab === 'login' ? 'Log In' : 'Create Account'}
            </motion.button>

            {/* Divider */}
            <div className="flex items-center gap-3 my-1">
              <div className="flex-1 h-px" style={{ background: 'var(--nh-border)' }} />
              <span className="text-xs" style={{ color: 'var(--nh-text-secondary)' }}>or continue with</span>
              <div className="flex-1 h-px" style={{ background: 'var(--nh-border)' }} />
            </div>

            {/* Google */}
            <a href={GOOGLE_OAUTH_URL}>
              <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                className="w-full flex items-center gap-3 py-2.5 px-4 rounded-xl cursor-pointer transition-all"
                style={{
                  background: 'var(--nh-bg)',
                  border: '1px solid var(--nh-border)',
                }}>
                {/* Google G */}
                <svg className="w-5 h-5 flex-shrink-0" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                <div className="flex-1 min-w-0">
                  {googleUser ? (
                    <>
                      <p className="text-xs font-semibold" style={{ color: 'var(--nh-text)' }}>
                        Sign in as {googleUser.split('@')[0]}
                      </p>
                      <p className="text-xs truncate" style={{ color: 'var(--nh-text-secondary)' }}>
                        {googleUser}
                      </p>
                    </>
                  ) : (
                    <p className="text-sm font-medium" style={{ color: 'var(--nh-text)' }}>
                      Sign in with Google
                    </p>
                  )}
                </div>
              </motion.div>
            </a>

          </div>
        </div>
      </motion.div>
    </div>
  );
}

// ── Reusable input field ──────────────────────────────────────────────────
function InputField({ icon: Icon, placeholder, type = 'text', value, onChange }) {
  return (
    <div className="relative">
      <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4"
        style={{ color: 'var(--nh-text-secondary)' }} />
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        className="w-full pl-10 pr-4 py-3 rounded-xl text-sm transition-all"
        style={{
          background: 'var(--nh-bg)',
          border: '1px solid var(--nh-border)',
          color: 'var(--nh-text)',
        }}
      />
    </div>
  );
}