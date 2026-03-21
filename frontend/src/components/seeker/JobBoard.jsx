import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Briefcase, MapPin, Clock, ExternalLink, Search,
  Filter, RefreshCw, Globe, Building2, Loader2, AlertCircle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useQuery } from '@tanstack/react-query';
import { jsonFetch } from '@/api/http';
import GlassCard from '@/components/shared/GlassCard';
import EmptyState from '@/components/shared/EmptyState';

// ── Remotive category map ─────────────────────────────────────────────────
const CATEGORIES = [
  { label: 'All', value: '' },
  { label: 'Software Dev', value: 'software-dev' },
  { label: 'Frontend', value: 'frontend' },
  { label: 'Backend', value: 'backend' },
  { label: 'Full Stack', value: 'fullstack' },
  { label: 'Data Science', value: 'data-science' },
  { label: 'DevOps / SysAdmin', value: 'devops-sysadmin' },
  { label: 'Mobile', value: 'mobile' },
  { label: 'QA', value: 'qa' },
];

// ── Job type badge ────────────────────────────────────────────────────────
function JobTypeBadge({ type }) {
  const t = (type || '').toLowerCase();
  const style = t.includes('full')
    ? { bg: 'rgba(139,184,168,0.15)', text: '#5a9e8a' }
    : t.includes('contract')
    ? { bg: 'rgba(212,165,116,0.15)', text: '#c4894a' }
    : t.includes('intern')
    ? { bg: 'rgba(124,158,201,0.15)', text: '#4a6fa5' }
    : { bg: 'rgba(139,184,168,0.15)', text: '#5a9e8a' };
  return (
    <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold flex-shrink-0"
      style={{ background: style.bg, color: style.text }}>
      {type || 'Full-time'}
    </span>
  );
}

// ── Time since posted ─────────────────────────────────────────────────────
function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days}d ago`;
  if (days < 30) return `${Math.floor(days / 7)}w ago`;
  return `${Math.floor(days / 30)}mo ago`;
}

// ── Job Card ──────────────────────────────────────────────────────────────
function JobCard({ job, index }) {
  const [expanded, setExpanded] = useState(false);

  // Strip HTML from description
  const plainDesc = job.description
    ? job.description.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
    : '';

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      className="rounded-2xl border flex flex-col transition-shadow hover:shadow-md"
      style={{ background: 'var(--nh-card)', borderColor: 'var(--nh-border)', boxShadow: 'var(--nh-shadow-sm)' }}
    >
      <div className="p-5">
        {/* Header */}
        <div className="flex items-start gap-3 mb-3">
          {/* Company logo or fallback */}
          <div className="w-11 h-11 rounded-xl overflow-hidden flex-shrink-0 border"
            style={{ borderColor: 'var(--nh-border)', background: 'var(--nh-bg)' }}>
            {job.company_logo ? (
              <img src={job.company_logo} alt={job.company_name}
                className="w-full h-full object-contain p-1"
                onError={e => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }} />
            ) : null}
            <div className="w-full h-full flex items-center justify-center"
              style={{ display: job.company_logo ? 'none' : 'flex' }}>
              <Building2 className="w-5 h-5" style={{ color: 'var(--nh-primary)' }} />
            </div>
          </div>

          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-base leading-snug mb-0.5"
              style={{ color: 'var(--nh-text)' }}>
              {job.title}
            </h3>
            <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>
              {job.company_name}
            </p>
          </div>

          <JobTypeBadge type={job.job_type} />
        </div>

        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-3 mb-3">
          {job.candidate_required_location && (
            <span className="flex items-center gap-1 text-xs"
              style={{ color: 'var(--nh-text-secondary)' }}>
              <MapPin className="w-3.5 h-3.5" />
              {job.candidate_required_location}
            </span>
          )}
          <span className="flex items-center gap-1 text-xs"
            style={{ color: 'var(--nh-text-secondary)' }}>
            <Globe className="w-3.5 h-3.5" /> Remote
          </span>
          {job.publication_date && (
            <span className="flex items-center gap-1 text-xs"
              style={{ color: 'var(--nh-text-secondary)' }}>
              <Clock className="w-3.5 h-3.5" />
              {timeAgo(job.publication_date)}
            </span>
          )}
        </div>

        {/* Tags */}
        {job.tags?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {job.tags.slice(0, 5).map((tag, i) => (
              <span key={i} className="px-2 py-0.5 rounded-md text-xs font-medium"
                style={{ background: 'var(--nh-primary-light)', color: 'var(--nh-primary)' }}>
                {tag.name || tag}
              </span>
            ))}
          </div>
        )}

        {/* Salary */}
        {job.salary && (
          <p className="text-xs font-semibold mb-3" style={{ color: '#5a9e8a' }}>
            💰 {job.salary}
          </p>
        )}

        {/* Description toggle */}
        {plainDesc && (
          <div className="mb-3">
            <p className="text-xs leading-relaxed" style={{ color: 'var(--nh-text-secondary)' }}>
              {expanded ? plainDesc.slice(0, 400) : plainDesc.slice(0, 120)}
              {plainDesc.length > 120 && (
                <button onClick={() => setExpanded(!expanded)}
                  className="ml-1 font-medium" style={{ color: 'var(--nh-primary)' }}>
                  {expanded ? ' show less' : '... read more'}
                </button>
              )}
            </p>
          </div>
        )}

        {/* Apply button */}
        <a href={job.url} target="_blank" rel="noopener noreferrer"
          className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl text-sm font-semibold text-white transition-opacity hover:opacity-90 mt-auto"
          style={{ background: 'linear-gradient(135deg, #6B9E96 0%, #4a7c74 100%)' }}>
          Apply Now <ExternalLink className="w-4 h-4" />
        </a>
      </div>
    </motion.div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ════════════════════════════════════════════════════════════════════════════
export default function JobBoard() {
  const [category, setCategory] = useState('software-dev');
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [total, setTotal] = useState(0);

  // Upcoming interviews from backend
  const { data: rawInterviews } = useQuery({
    queryKey: ['my-interviews'],
    queryFn: () => jsonFetch('/api/interviews/'),
    initialData: [],
  });
  const interviews = Array.isArray(rawInterviews)
    ? rawInterviews
    : (rawInterviews?.results || []);
  const upcomingInterviews = interviews.filter(i => i.status === 'scheduled');

  // ── Fetch from Remotive API ───────────────────────────────────────────
  const fetchJobs = useCallback(async (cat, q) => {
    setLoading(true);
    setError('');
    try {
      // Build Remotive URL — free, no API key needed
      let url = 'https://remotive.com/api/remote-jobs?limit=20';
      if (cat) url += `&category=${encodeURIComponent(cat)}`;
      if (q) url += `&search=${encodeURIComponent(q)}`;

      const res = await fetch(url);
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = await res.json();
      setJobs(data.jobs || []);
      setTotal(data['job-count'] || data.jobs?.length || 0);
    } catch (err) {
      console.error('Job fetch error:', err);
      setError('Could not load jobs. Please check your connection and try again.');
      setJobs([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch on mount and category change
  useEffect(() => {
    fetchJobs(category, search);
  }, [category]);

  const handleSearch = () => {
    setSearch(searchInput);
    fetchJobs(category, searchInput);
  };

  return (
    <div className="space-y-6">

      {/* ── Upcoming Interviews ── */}
      {upcomingInterviews.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3" style={{ color: 'var(--nh-text)' }}>
            Your Upcoming Interviews
          </h2>
          <div className="space-y-2">
            {upcomingInterviews.slice(0, 3).map(interview => (
              <div key={interview.id}
                className="rounded-2xl p-4 border flex items-center justify-between flex-wrap gap-3"
                style={{ background: 'var(--nh-card)', borderColor: 'var(--nh-border)' }}>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                    style={{ background: 'var(--nh-primary-light)' }}>
                    <Briefcase className="w-5 h-5" style={{ color: 'var(--nh-primary)' }} />
                  </div>
                  <div>
                    <h3 className="font-semibold" style={{ color: 'var(--nh-text)' }}>
                      {interview.role || 'Interview'}
                    </h3>
                    <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>
                      {interview.scheduled_date
                        ? new Date(interview.scheduled_date).toLocaleDateString('en-US', {
                            weekday: 'short', month: 'short', day: 'numeric',
                            hour: '2-digit', minute: '2-digit',
                          })
                        : 'TBD'}
                    </p>
                  </div>
                </div>
                <span className="px-3 py-1 rounded-full text-xs font-semibold"
                  style={{ background: 'rgba(124,158,201,0.15)', color: '#4a6fa5' }}>
                  Scheduled
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Search + Filter bar ── */}
      <div className="flex flex-col gap-3">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4"
              style={{ color: 'var(--nh-text-secondary)' }} />
            <Input
              value={searchInput}
              onChange={e => setSearchInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              placeholder="Search jobs, skills, company..."
              className="rounded-xl pl-9"
              style={{ borderColor: 'var(--nh-border)', background: 'var(--nh-card)', color: 'var(--nh-text)' }}
            />
          </div>
          <Button onClick={handleSearch} disabled={loading}
            className="rounded-xl gradient-bg text-white px-5">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          </Button>
          <Button onClick={() => fetchJobs(category, search)} variant="outline"
            disabled={loading} className="rounded-xl px-3"
            style={{ borderColor: 'var(--nh-border)', color: 'var(--nh-text)' }}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        {/* Category pills */}
        <div className="flex flex-wrap gap-2">
          {CATEGORIES.map(cat => (
            <button key={cat.value}
              onClick={() => setCategory(cat.value)}
              className="px-3 py-1.5 rounded-xl text-xs font-medium transition-all"
              style={{
                background: category === cat.value ? 'linear-gradient(135deg, #6B9E96, #4a7c74)' : 'var(--nh-card)',
                color: category === cat.value ? '#fff' : 'var(--nh-text-secondary)',
                border: `1px solid ${category === cat.value ? 'transparent' : 'var(--nh-border)'}`,
              }}>
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Results header ── */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold" style={{ color: 'var(--nh-text)' }}>
          {search ? `Results for "${search}"` : 'Latest Remote Opportunities'}
          {total > 0 && !loading && (
            <span className="ml-2 text-sm font-normal" style={{ color: 'var(--nh-text-secondary)' }}>
              ({jobs.length} shown)
            </span>
          )}
        </h2>
        <span className="text-xs px-2 py-1 rounded-lg"
          style={{ background: 'rgba(139,184,168,0.15)', color: '#5a9e8a' }}>
          via Remotive.com
        </span>
      </div>

      {/* ── Error ── */}
      {error && (
        <div className="flex items-center gap-2 p-4 rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" /> {error}
        </div>
      )}

      {/* ── Loading skeleton ── */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="rounded-2xl p-5 border animate-pulse"
              style={{ background: 'var(--nh-card)', borderColor: 'var(--nh-border)', height: '200px' }}>
              <div className="flex gap-3 mb-3">
                <div className="w-11 h-11 rounded-xl" style={{ background: 'var(--nh-border)' }} />
                <div className="flex-1 space-y-2">
                  <div className="h-4 rounded" style={{ background: 'var(--nh-border)', width: '70%' }} />
                  <div className="h-3 rounded" style={{ background: 'var(--nh-border)', width: '50%' }} />
                </div>
              </div>
              <div className="space-y-2">
                <div className="h-3 rounded" style={{ background: 'var(--nh-border)' }} />
                <div className="h-3 rounded" style={{ background: 'var(--nh-border)', width: '80%' }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Job grid ── */}
      {!loading && !error && jobs.length === 0 && (
        <EmptyState icon={Briefcase} title="No Jobs Found"
          description="Try a different category or search term." />
      )}

      {!loading && jobs.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {jobs.map((job, i) => (
            <JobCard key={job.id} job={job} index={i} />
          ))}
        </div>
      )}

      {/* ── Footer note ── */}
      {!loading && jobs.length > 0 && (
        <p className="text-center text-xs pb-4" style={{ color: 'var(--nh-text-secondary)' }}>
          Jobs powered by <a href="https://remotive.com" target="_blank" rel="noopener noreferrer"
            className="underline" style={{ color: 'var(--nh-primary)' }}>Remotive.com</a> — updated daily
        </p>
      )}
    </div>
  );
}