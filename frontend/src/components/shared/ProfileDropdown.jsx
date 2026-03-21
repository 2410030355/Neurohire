import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LogOut, Settings, ChevronDown, Sun, Moon } from 'lucide-react';
import { jsonFetch } from '@/api/http';

/**
 * ProfileDropdown — includes the ONE ThemeToggle for the whole app.
 * ThemeToggle has been removed from Sidebar and SeekerSidebar.
 */
function useTheme() {
  const [light, setLight] = useState(() => localStorage.getItem('nh-theme') === 'light');

  useEffect(() => {
    const root = document.documentElement;
    if (light) {
      root.setAttribute('data-theme', 'light');
      root.classList.remove('dark');
    } else {
      root.removeAttribute('data-theme');
      root.classList.add('dark');
    }
    localStorage.setItem('nh-theme', light ? 'light' : 'dark');
  }, [light]);

  return [light, () => setLight(v => !v)];
}

export default function ProfileDropdown({ role: roleProp = 'jobseeker' }) {
  const [user, setUser]   = useState(() => {
    try { return JSON.parse(localStorage.getItem('user') || 'null'); } catch { return null; }
  });
  const [open, setOpen]   = useState(false);
  const [light, toggleTheme] = useTheme();
  const ref = useRef(null);

  useEffect(() => {
    // Always fetch fresh user data from backend on mount
    jsonFetch('/api/auth/me/').then(data => {
      if (data?.id || data?.email) {
        setUser(data);
        localStorage.setItem('user', JSON.stringify(data));
      }
    }).catch(() => {
      // If /me/ fails, user is not logged in — clear stale data
      const stored = localStorage.getItem('user');
      if (stored) setUser(JSON.parse(stored));
    });
  }, []);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const role = user?.role || roleProp;
  const initials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : (user?.email?.[0] || 'U').toUpperCase();

  const displayName = (
    user?.full_name?.trim() ||
    (user?.first_name ? `${user.first_name} ${user?.last_name || ''}`.trim() : null) ||
    user?.email?.split('@')[0] ||
    user?.username ||
    'User'
  );

  const roleBadge = role === 'recruiter'
    ? { label: 'Recruiter', color: 'var(--nh-secondary)' }
    : { label: 'Job Seeker', color: 'var(--nh-primary)' };

  return (
    <div className="flex items-center gap-2" ref={ref}>

      {/* ── Theme toggle — ONE place in the whole app ── */}
      <motion.button
        whileHover={{ scale: 1.08 }} whileTap={{ scale: 0.92 }}
        onClick={toggleTheme}
        className="w-9 h-9 rounded-xl flex items-center justify-center transition-all"
        style={{ background: 'var(--nh-primary-light)', border: '1px solid var(--nh-border)' }}
        aria-label="Toggle theme"
        title={light ? 'Switch to dark mode' : 'Switch to light mode'}
      >
        {light
          ? <Moon className="w-4 h-4" style={{ color: 'var(--nh-primary)' }} />
          : <Sun  className="w-4 h-4" style={{ color: 'var(--nh-primary)' }} />
        }
      </motion.button>

      {/* ── Avatar button ── */}
      <div className="relative">
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center gap-2 px-2 py-1.5 rounded-xl transition-all"
          style={{ border: '1px solid var(--nh-border)', background: 'var(--nh-card)' }}
        >
          <div className="w-7 h-7 rounded-full gradient-bg flex items-center justify-center flex-shrink-0">
            <span className="text-xs font-bold text-white">{initials}</span>
          </div>
          <span className="hidden md:block text-sm font-medium max-w-[100px] truncate"
            style={{ color: 'var(--nh-text)' }}>
            {displayName}
          </span>
          <ChevronDown className="w-3.5 h-3.5 hidden md:block" style={{ color: 'var(--nh-text-secondary)' }} />
        </button>

        {/* ── Dropdown ── */}
        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.97 }}
              transition={{ duration: 0.15 }}
              className="absolute right-0 top-12 w-64 rounded-2xl z-[200] overflow-hidden"
              style={{
                background: 'var(--nh-card)',
                border: '1px solid var(--nh-border)',
                boxShadow: 'var(--nh-shadow-lg)',
              }}
            >
              {/* Header */}
              <div className="p-4 border-b" style={{
                borderColor: 'var(--nh-border)',
                background: 'linear-gradient(135deg, var(--nh-primary-light), var(--nh-secondary-light))',
              }}>
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-full gradient-bg flex items-center justify-center flex-shrink-0 shadow-md">
                    <span className="text-sm font-bold text-white">{initials}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold truncate" style={{ color: 'var(--nh-text)' }}>
                      {user?.full_name || displayName}
                    </p>
                    <p className="text-xs truncate" style={{ color: 'var(--nh-text-secondary)' }}>
                      {user?.email || ''}
                    </p>
                    <span className="inline-block mt-1 text-[10px] font-semibold px-2 py-0.5 rounded-full"
                      style={{ background: `${roleBadge.color}20`, color: roleBadge.color }}>
                      {roleBadge.label}
                    </span>
                  </div>
                </div>
              </div>

              {/* Menu */}
              <div className="p-2">
                <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all text-left"
                  style={{ color: 'var(--nh-text-secondary)' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--nh-border-light)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <Settings className="w-4 h-4 flex-shrink-0" />
                  <span className="text-sm">Settings</span>
                  <span className="ml-auto text-xs" style={{ color: 'var(--nh-text-secondary)' }}>Soon</span>
                </button>

                <button
                  onClick={async () => {
                    try { await jsonFetch('/api/auth/logout/', { method: 'POST' }); } catch {}
                    localStorage.removeItem('user');
                    window.location.href = '/';
                  }}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all text-left mt-1"
                  style={{ color: 'var(--nh-danger)' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(248,113,113,0.08)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <LogOut className="w-4 h-4 flex-shrink-0" />
                  <span className="text-sm">Sign out</span>
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}