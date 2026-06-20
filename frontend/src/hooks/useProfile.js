/**
 * useProfile — shared hook for RecruiterProfileDropdown and SeekerProfileDropdown
 *
 * Flow:
 * 1. Never trust localStorage on mount — always verify against live session
 * 2. Fetch from /api/auth/me/ then /api/auth/profile/ for extra fields
 * 3. If full_name is missing (rare, e.g. Google returned nothing), derive from email
 * 4. expectedRole param guards against showing a recruiter's data on the seeker
 *    dashboard or vice versa — e.g. if a recruiter visits /SeekerDashboard directly
 * 5. saveProfile() PATCHes /api/auth/profile/ and updates localStorage
 */
import { useState, useEffect } from 'react';
import { API_BASE_URL } from '@/api/http';

export function extractNameFromEmail(email = '') {
  if (!email) return '';
  const local = email.split('@')[0];
  return local
    .replace(/[._\-]/g, ' ')
    .replace(/\d+/g, '')
    .trim()
    .split(' ')
    .filter(Boolean)
    .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ') || local;
}

async function apiFetch(path, options = {}) {
  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const text = await res.text();
  try { return { ok: res.ok, status: res.status, data: JSON.parse(text) }; }
  catch { return { ok: res.ok, status: res.status, data: text }; }
}

/**
 * @param {string} expectedRole - 'recruiter' | 'jobseeker'
 *   If the live session's role doesn't match, user is set to null
 *   (dropdown shows a "wrong dashboard" state instead of someone else's name)
 */
export function useProfile(expectedRole) {
  const [user,        setUser]        = useState(null);
  const [roleMismatch, setRoleMismatch] = useState(false);
  const [saving,       setSaving]       = useState(false);
  const [error,        setError]        = useState('');

  useEffect(() => {
    let cancelled = false;

    apiFetch('/api/auth/me/').then(({ ok, data }) => {
      if (cancelled) return;

      if (!ok || !data?.email) {
        setUser(null);
        setRoleMismatch(false);
        localStorage.removeItem('user');
        return;
      }

      // Guard: this dashboard expects a specific role
      if (expectedRole && data.role && data.role !== expectedRole) {
        console.warn(`[useProfile] role mismatch: session is "${data.role}", dashboard expects "${expectedRole}"`);
        setUser(null);
        setRoleMismatch(true);
        return;
      }

      if (!data.full_name?.trim()) {
        data.full_name = extractNameFromEmail(data.email);
      }

      // Pull extra profile fields (phone, company, college, etc.)
      apiFetch('/api/auth/profile/').then(({ ok: ok2, data: data2 }) => {
        if (cancelled) return;
        const merged = ok2 && data2?.email ? { ...data, ...data2 } : data;
        if (!merged.full_name?.trim()) merged.full_name = extractNameFromEmail(merged.email);
        setUser(merged);
        setRoleMismatch(false);
        localStorage.setItem('user', JSON.stringify(merged));
      }).catch(() => {
        setUser(data);
        setRoleMismatch(false);
        localStorage.setItem('user', JSON.stringify(data));
      });
    }).catch(() => {
      if (cancelled) return;
      setUser(null);
      localStorage.removeItem('user');
    });

    return () => { cancelled = true; };
  }, [expectedRole]);

  const saveProfile = async (updates) => {
    setSaving(true);
    setError('');
    try {
      const { ok, data } = await apiFetch('/api/auth/profile/', {
        method: 'PATCH',
        body: JSON.stringify(updates),
      });
      if (!ok) throw new Error(data?.error || 'Save failed');
      if (!data.full_name?.trim()) data.full_name = extractNameFromEmail(data.email);
      setUser(prev => ({ ...prev, ...data }));
      localStorage.setItem('user', JSON.stringify({ ...user, ...data }));
      return true;
    } catch (e) {
      setError(e.message);
      return false;
    } finally {
      setSaving(false);
    }
  };

  const displayName = (
    user?.full_name?.trim() ||
    extractNameFromEmail(user?.email) ||
    user?.username ||
    'User'
  );

  const initials = displayName
    .split(' ')
    .filter(Boolean)
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) || '?';

  return { user, displayName, initials, saving, error, roleMismatch, saveProfile };
}