import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronDown, Sun, Moon, LogOut, Pencil, X,
  Save, Building2, Phone, MapPin, Linkedin, Briefcase
} from 'lucide-react';
import { jsonFetch } from '@/api/http';
import { useProfile } from '@/hooks/useProfile';
import { useTheme } from '@/hooks/useTheme';

export default function RecruiterProfileDropdown() {
  const { user, displayName, initials, saving, error, saveProfile } = useProfile();
  const [light, toggleTheme] = useTheme();
  const [open,    setOpen]   = useState(false);
  const [editing, setEditing] = useState(false);
  const ref = useRef(null);

  const [form, setForm] = useState({
    full_name: '', job_title: '', company: '',
    phone: '', location: '', linkedin: '', bio: '',
  });

  // Sync form when user loads
  useEffect(() => {
    if (user) setForm({
      full_name: user.full_name  || '',
      job_title: user.job_title  || '',
      company:   user.company    || '',
      phone:     user.phone      || '',
      location:  user.location   || '',
      linkedin:  user.linkedin   || '',
      bio:       user.bio        || '',
    });
  }, [user]);

  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) { setOpen(false); setEditing(false); } };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  const handleSave = async () => {
    const ok = await saveProfile(form);
    if (ok) setEditing(false);
  };

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  return (
    <div className="flex items-center gap-2" ref={ref}>

      {/* Theme toggle */}
      <motion.button whileHover={{ scale: 1.08 }} whileTap={{ scale: 0.92 }}
        onClick={toggleTheme}
        className="w-9 h-9 rounded-xl flex items-center justify-center"
        style={{ background: 'var(--nh-primary-light)', border: '1px solid var(--nh-border)' }}>
        {light
          ? <Moon className="w-4 h-4" style={{ color: 'var(--nh-primary)' }} />
          : <Sun  className="w-4 h-4" style={{ color: 'var(--nh-primary)' }} />}
      </motion.button>

      {/* Avatar */}
      <div className="relative">
        <button onClick={() => { setOpen(!open); setEditing(false); }}
          className="flex items-center gap-2 px-2 py-1.5 rounded-xl transition-all"
          style={{ border: '1px solid var(--nh-border)', background: 'var(--nh-card)' }}>
          <div className="w-7 h-7 rounded-full gradient-bg flex items-center justify-center flex-shrink-0">
            <span className="text-xs font-bold text-white">{initials}</span>
          </div>
          <span className="hidden md:block text-sm font-medium max-w-[120px] truncate"
            style={{ color: 'var(--nh-text)' }}>{displayName}</span>
          <ChevronDown className="w-3.5 h-3.5 hidden md:block" style={{ color: 'var(--nh-text-secondary)' }} />
        </button>

        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.97 }}
              transition={{ duration: 0.15 }}
              className="absolute right-0 top-12 w-80 rounded-2xl z-[200] overflow-hidden"
              style={{ background: 'var(--nh-card)', border: '1px solid var(--nh-border)', boxShadow: 'var(--nh-shadow-lg)' }}>

              {/* ── Header ── */}
              <div className="p-4 border-b" style={{
                borderColor: 'var(--nh-border)',
                background: 'linear-gradient(135deg, var(--nh-primary-light), var(--nh-secondary-light))',
              }}>
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-full gradient-bg flex items-center justify-center flex-shrink-0 shadow-md">
                    <span className="text-base font-bold text-white">{initials}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-bold truncate" style={{ color: 'var(--nh-text)' }}>
                      {displayName}
                    </p>
                    <p className="text-xs truncate" style={{ color: 'var(--nh-text-secondary)' }}>
                      {user?.email}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                        style={{ background: 'rgba(167,139,250,0.15)', color: 'var(--nh-secondary)' }}>
                        Recruiter
                      </span>
                      {user?.company && (
                        <span className="text-[10px] truncate" style={{ color: 'var(--nh-text-secondary)' }}>
                          {user.company}
                        </span>
                      )}
                    </div>
                  </div>
                  <button onClick={() => setEditing(!editing)}
                    className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{ background: 'var(--nh-primary-light)' }}>
                    {editing
                      ? <X className="w-4 h-4" style={{ color: 'var(--nh-primary)' }} />
                      : <Pencil className="w-4 h-4" style={{ color: 'var(--nh-primary)' }} />}
                  </button>
                </div>
              </div>

              {/* ── View mode ── */}
              {!editing && (
                <div className="p-3 space-y-1.5">
                  {user?.job_title && <InfoRow icon={Briefcase} value={user.job_title} />}
                  {user?.company   && <InfoRow icon={Building2} value={user.company} />}
                  {user?.phone     && <InfoRow icon={Phone}     value={user.phone} />}
                  {user?.location  && <InfoRow icon={MapPin}    value={user.location} />}
                  {user?.linkedin  && (
                    <InfoRow icon={Linkedin} value={user.linkedin}
                      link={user.linkedin.startsWith('http') ? user.linkedin : `https://${user.linkedin}`} />
                  )}
                  {!user?.job_title && !user?.company && !user?.phone && (
                    <p className="text-xs text-center py-2" style={{ color: 'var(--nh-text-secondary)' }}>
                      Click ✏️ to add your details
                    </p>
                  )}
                  <Divider />
                  <SignOutBtn />
                </div>
              )}

              {/* ── Edit mode ── */}
              {editing && (
                <div className="p-3 space-y-2 max-h-80 overflow-y-auto nh-scrollbar">
                  <EditField label="Full Name"   value={form.full_name} onChange={set('full_name')} placeholder="Your full name" />
                  <EditField label="Job Title"   value={form.job_title} onChange={set('job_title')} placeholder="e.g. HR Manager" />
                  <EditField label="Company"     value={form.company}   onChange={set('company')}   placeholder="e.g. Infosys" />
                  <EditField label="Phone"       value={form.phone}     onChange={set('phone')}     placeholder="+91 98765 43210" />
                  <EditField label="Location"    value={form.location}  onChange={set('location')}  placeholder="e.g. Hyderabad, India" />
                  <EditField label="LinkedIn"    value={form.linkedin}  onChange={set('linkedin')}  placeholder="linkedin.com/in/yourname" />
                  {error && <p className="text-xs" style={{ color: 'var(--nh-danger)' }}>{error}</p>}
                  <button onClick={handleSave} disabled={saving}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold text-white mt-1"
                    style={{ background: 'linear-gradient(135deg, #2DD4BF, #A78BFA)', opacity: saving ? 0.7 : 1 }}>
                    <Save className="w-4 h-4" />
                    {saving ? 'Saving…' : 'Save Profile'}
                  </button>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function InfoRow({ icon: Icon, value, link }) {
  return (
    <div className="flex items-center gap-2.5 px-1">
      <Icon className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--nh-text-secondary)' }} />
      {link
        ? <a href={link} target="_blank" rel="noopener noreferrer"
            className="text-xs truncate hover:underline" style={{ color: 'var(--nh-primary)' }}>{value}</a>
        : <span className="text-xs truncate" style={{ color: 'var(--nh-text)' }}>{value}</span>}
    </div>
  );
}

function EditField({ label, value, onChange, placeholder }) {
  return (
    <div>
      <label className="text-[10px] font-semibold uppercase tracking-wider mb-1 block"
        style={{ color: 'var(--nh-text-secondary)' }}>{label}</label>
      <input value={value} onChange={onChange} placeholder={placeholder}
        className="w-full px-3 py-2 rounded-xl text-sm"
        style={{ background: 'var(--nh-bg)', border: '1px solid var(--nh-border)', color: 'var(--nh-text)' }} />
    </div>
  );
}

function Divider() {
  return <div className="my-1" style={{ borderTop: '1px solid var(--nh-border)' }} />;
}

function SignOutBtn() {
  return (
    <button
      onClick={async () => {
        try { await jsonFetch('/api/auth/logout/', { method: 'POST' }); } catch {}
        localStorage.removeItem('user');
        window.location.href = '/';
      }}
      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all text-left"
      style={{ color: 'var(--nh-danger)' }}
      onMouseEnter={e => e.currentTarget.style.background = 'rgba(248,113,113,0.08)'}
      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
      <LogOut className="w-4 h-4" />
      <span className="text-sm">Sign out</span>
    </button>
  );
}