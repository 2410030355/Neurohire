/**
 * useProfile — shared hook for RecruiterProfileDropdown and SeekerProfileDropdown
 *
 * Flow:
 * 1. Read cached user from localStorage immediately (instant display)
 * 2. Fetch fresh data from /api/auth/profile/ in background
 * 3. If name is missing, derive it from email
 * 4. saveProfile() PATCHes /api/auth/profile/ and updates localStorage
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
  console.log(`[useProfile] ${options.method || 'GET'} ${url}`);
  const res = await fetch(url, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  console.log(`[useProfile] ${path} → ${res.status}`);
  const text = await res.text();
  try { return { ok: res.ok, status: res.status, data: JSON.parse(text) }; }
  catch { return { ok: res.ok, status: res.status, data: text }; }
}

export function useProfile() {
  const [user,   setUser]   = useState(() => {
    try { return JSON.parse(localStorage.getItem('user') || 'null'); } catch { return null; }
  });
  const [saving, setSaving] = useState(false);
  const [error,  setError]  = useState('');

  useEffect(() => {
    apiFetch('/api/auth/me/').then(({ ok, data }) => {
      if (!ok || !data?.email) {
        console.warn('[useProfile] /me/ failed or no email — using localStorage');
        return;
      }
      // Derive name from email if backend returned blank full_name
      if (!data.full_name?.trim()) {
        data.full_name = extractNameFromEmail(data.email);
      }
      setUser(data);
      localStorage.setItem('user', JSON.stringify(data));
    }).catch(e => {
      console.warn('[useProfile] /me/ fetch error:', e.message);
    });
  }, []);

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
      setUser(data);
      localStorage.setItem('user', JSON.stringify(data));
      return true;
    } catch (e) {
      setError(e.message);
      return false;
    } finally {
      setSaving(false);
    }
  };

  // displayName never shows "User" — always at least email prefix
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

  return { user, displayName, initials, saving, error, saveProfile };
}