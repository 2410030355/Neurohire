/**
 * useProfile — shared hook for both RecruiterProfileDropdown and SeekerProfileDropdown
 * Fetches user from /api/auth/profile/ (richer than /me/),
 * extracts name from email if full_name is missing,
 * and exposes save() to update profile details.
 */
import { useState, useEffect } from 'react';
import { jsonFetch } from '@/api/http';

export function extractNameFromEmail(email = '') {
  if (!email) return '';
  const local = email.split('@')[0];
  // Convert "john.doe" or "john_doe" or "johndoe123" → "John Doe" / "John"
  return local
    .replace(/[._\-]/g, ' ')
    .replace(/\d+/g, '')
    .trim()
    .split(' ')
    .filter(Boolean)
    .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ') || local;
}

export function useProfile() {
  const [user, setUser]       = useState(() => {
    try { return JSON.parse(localStorage.getItem('user') || 'null'); } catch { return null; }
  });
  const [saving, setSaving]   = useState(false);
  const [error,  setError]    = useState('');

  useEffect(() => {
    jsonFetch('/api/auth/profile/')
      .then(data => {
        if (!data?.email) return;
        // If full_name is empty, derive from email
        if (!data.full_name?.trim()) {
          data.full_name = extractNameFromEmail(data.email);
        }
        setUser(data);
        localStorage.setItem('user', JSON.stringify(data));
      })
      .catch(() => {
        const stored = localStorage.getItem('user');
        if (stored) {
          const parsed = JSON.parse(stored);
          if (!parsed.full_name?.trim()) {
            parsed.full_name = extractNameFromEmail(parsed.email);
          }
          setUser(parsed);
        }
      });
  }, []);

  const saveProfile = async (updates) => {
    setSaving(true);
    setError('');
    try {
      const data = await jsonFetch('/api/auth/profile/', {
        method: 'PATCH',
        body: JSON.stringify(updates),
      });
      if (!data.full_name?.trim()) data.full_name = extractNameFromEmail(data.email);
      setUser(data);
      localStorage.setItem('user', JSON.stringify(data));
      return true;
    } catch (e) {
      setError(e.message || 'Failed to save');
      return false;
    } finally {
      setSaving(false);
    }
  };

  const displayName = (
    user?.full_name?.trim() ||
    extractNameFromEmail(user?.email) ||
    'User'
  );

  const initials = displayName
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) || 'U';

  return { user, displayName, initials, saving, error, saveProfile };
}