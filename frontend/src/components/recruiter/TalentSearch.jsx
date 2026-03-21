import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Github, Globe, Search, Loader2, ExternalLink, Star, Code2, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { jsonFetch } from '@/api/http';
import { toast } from 'sonner';
import GlassCard from '@/components/shared/GlassCard';
import ScoreRing from '@/components/shared/ScoreRing';
import FitBadge from '@/components/shared/FitBadge';

const PORTAL_SOURCES = ['LinkedIn', 'Internshala', 'Naukri', 'Indeed'];

// ─── GitHub Candidate Card ─────────────────────────────────────────────────
function GitHubCandidateCard({ candidate, onSchedule, onWaitlist, index }) {
  const username = candidate.github_url
    ? candidate.github_url.replace('https://github.com/', '').replace(/\/$/, '')
    : candidate.name?.toLowerCase().replace(/\s+/g, '') || 'developer';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
      className="rounded-2xl p-5 border relative transition-shadow hover:shadow-[var(--nh-shadow)]"
      style={{ background: 'var(--nh-card)', borderColor: 'var(--nh-border)', boxShadow: 'var(--nh-shadow-sm)' }}
    >
      <span className="absolute top-4 right-4 flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold"
        style={{ background: 'var(--nh-primary-light)', color: 'var(--nh-primary)', border: '1px solid var(--nh-border-light)' }}>
        <Github className="w-3 h-3" /> GitHub
      </span>

      <div className="flex items-center gap-3 mb-4 pr-20">
        <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: 'var(--nh-primary-light)' }}>
          <Github className="w-6 h-6" style={{ color: 'var(--nh-primary)' }} />
        </div>
        <div className="min-w-0">
          <h3 className="font-semibold text-base truncate" style={{ color: 'var(--nh-text)' }}>{candidate.name}</h3>
          <p className="text-sm truncate" style={{ color: 'var(--nh-text-secondary)' }}>
            @{username} • {candidate.experience_years || 0}y exp
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4 mb-4 flex-wrap">
        <ScoreRing score={candidate.role_match_score || 0} size={52} label="Role Match" />
        <ScoreRing score={candidate.skill_validation_score || 0} size={52} label="Skills" />
        <div className="flex flex-col items-center gap-1">
          <div className="flex items-center gap-1 px-3 py-1 rounded-lg" style={{ background: 'var(--nh-primary-light)', color: 'var(--nh-primary)' }}>
            <Star className="w-4 h-4" />
            <span className="text-sm font-bold">{candidate.repo_score || 0}</span>
          </div>
          <span className="text-xs" style={{ color: 'var(--nh-text-secondary)' }}>Repo Score</span>
        </div>
        <div className="flex flex-col items-center gap-1">
          <FitBadge level={candidate.final_fit || 'Medium'} />
          <span className="text-xs" style={{ color: 'var(--nh-text-secondary)' }}>Fit</span>
        </div>
      </div>

      {candidate.skills?.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {candidate.skills.slice(0, 6).map((s, i) => (
            <span key={i} className="px-2.5 py-1 rounded-lg text-xs font-medium"
              style={{ background: 'var(--nh-primary-light)', color: 'var(--nh-primary)', border: '1px solid var(--nh-border-light)' }}>
              <Code2 className="w-2.5 h-2.5 inline mr-1" />{s}
            </span>
          ))}
        </div>
      )}

      {candidate.profile_summary && (
        <p className="text-xs mb-4 leading-relaxed" style={{ color: 'var(--nh-text-secondary)' }}>
          {candidate.profile_summary}
        </p>
      )}

      <div className="flex items-center gap-2 flex-wrap pt-1">
        <a
          href={candidate.github_url || `https://github.com/${username}`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium border transition-opacity hover:opacity-90"
          style={{ borderColor: 'var(--nh-border)', color: 'var(--nh-text)', background: 'var(--nh-bg)' }}
        >
          <Github className="w-3.5 h-3.5" /> View Profile <ExternalLink className="w-3 h-3" />
        </a>
        <Button size="sm" onClick={() => onSchedule(candidate)} className="gradient-bg text-white rounded-xl font-medium shadow-sm">
          Schedule
        </Button>
        <Button size="sm" variant="outline" onClick={() => onWaitlist(candidate)} className="rounded-xl font-medium"
          style={{ borderColor: 'var(--nh-border)', color: 'var(--nh-text)' }}>
          Waitlist
        </Button>
      </div>
    </motion.div>
  );
}

// ─── Job Portal Candidate Card ─────────────────────────────────────────────
function PortalCandidateCard({ candidate, onSchedule, onWaitlist, index }) {
  const portal = candidate.portal_source || PORTAL_SOURCES[index % PORTAL_SOURCES.length];
  const portalColors = {
    LinkedIn:    { bg: 'var(--nh-primary-light)', text: 'var(--nh-primary)', border: 'var(--nh-border)' },
    Internshala: { bg: '#ECFDF5', text: '#065F46', border: '#A7F3D0' },
    Naukri:      { bg: '#FFF7ED', text: '#B45309', border: '#FED7AA' },
    Indeed:      { bg: '#F5F3FF', text: '#5A6C7D', border: 'var(--nh-border)' },
  };
  const pc = portalColors[portal] || portalColors.LinkedIn;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
      className="rounded-2xl p-5 border relative transition-shadow hover:shadow-[var(--nh-shadow)]"
      style={{ background: 'var(--nh-card)', borderColor: 'var(--nh-border)', boxShadow: 'var(--nh-shadow-sm)' }}
    >
      <span className="absolute top-4 right-4 flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border"
        style={{ background: pc.bg, color: pc.text, borderColor: pc.border }}>
        <Globe className="w-3 h-3" /> {portal}
      </span>

      <div className="flex items-center gap-3 mb-4 pr-24">
        <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: pc.bg }}>
          <User className="w-6 h-6" style={{ color: pc.text }} />
        </div>
        <div className="min-w-0">
          <h3 className="font-semibold text-base truncate" style={{ color: 'var(--nh-text)' }}>{candidate.name}</h3>
          <p className="text-sm truncate" style={{ color: 'var(--nh-text-secondary)' }}>
            {candidate.target_role} • {candidate.experience_years || 0}y exp
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4 mb-4 flex-wrap">
        <ScoreRing score={candidate.role_match_score || 0} size={52} label="Role Match" />
        <ScoreRing score={candidate.consistency_score || 0} size={52} label="Consistency" />
        <div className="flex flex-col items-center gap-1">
          <FitBadge level={candidate.final_fit || 'Medium'} />
          <span className="text-xs" style={{ color: 'var(--nh-text-secondary)' }}>Fit</span>
        </div>
        <div className="flex flex-col items-center gap-1">
          <FitBadge level={candidate.learning_velocity || 'Medium'} />
          <span className="text-xs" style={{ color: 'var(--nh-text-secondary)' }}>Velocity</span>
        </div>
      </div>

      {candidate.skills?.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {candidate.skills.slice(0, 6).map((s, i) => (
            <span key={i} className="px-2.5 py-1 rounded-lg text-xs font-medium"
              style={{ background: 'var(--nh-primary-light)', color: 'var(--nh-primary)', border: '1px solid var(--nh-border-light)' }}>
              {s}
            </span>
          ))}
        </div>
      )}

      {candidate.profile_summary && (
        <p className="text-xs mb-4 leading-relaxed" style={{ color: 'var(--nh-text-secondary)' }}>
          {candidate.profile_summary}
        </p>
      )}

      <div className="flex items-center gap-2 flex-wrap pt-1">
        <a
          href={`https://www.${portal.toLowerCase()}.com`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium border transition-opacity hover:opacity-90"
          style={{ borderColor: 'var(--nh-border)', color: 'var(--nh-text)', background: 'var(--nh-bg)' }}
        >
          View on {portal} <ExternalLink className="w-3 h-3 ml-1" />
        </a>
        <Button size="sm" onClick={() => onSchedule(candidate)} className="gradient-bg text-white rounded-xl font-medium shadow-sm">
          Schedule
        </Button>
        <Button size="sm" variant="outline" onClick={() => onWaitlist(candidate)} className="rounded-xl font-medium"
          style={{ borderColor: 'var(--nh-border)', color: 'var(--nh-text)' }}>
          Waitlist
        </Button>
      </div>
    </motion.div>
  );
}

// ─── Main TalentSearch ─────────────────────────────────────────────────────
export default function TalentSearch({ onSchedule, onWaitlist }) {
  const [searchType, setSearchType] = useState(null);
  const [role, setRole] = useState('');
  const [skills, setSkills] = useState('');
  const [expRange, setExpRange] = useState('');
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState([]);

  const handleSearch = async () => {
    if (!role.trim()) return toast.error('Please specify a role');
    setSearching(true);
    setResults([]);
    try {
      const response = await jsonFetch('/api/talent-search/', {
        method: 'POST',
        body: JSON.stringify({
          search_type: searchType,
          role,
          skills: skills || undefined,
          exp_range: expRange || undefined,
        }),
      });
      const list = Array.isArray(response?.candidates)
        ? response.candidates
        : Array.isArray(response)
        ? response
        : [];
      setResults(list);
      if (list.length === 0) {
        toast.info('No candidates found — try a different role or skills');
      } else {
        toast.success(`Found ${list.length} candidates`);
      }
    } catch (err) {
      console.error('Talent search error:', err);
      toast.error(err?.message || 'Search failed — check console');
    } finally {
      setSearching(false);
    }
  };

  if (!searchType) {
    return (
      <div className="mb-8">
        <h2 className="text-xl font-bold mb-2" style={{ color: 'var(--nh-text)' }}>External Talent Search</h2>
        <p className="text-sm mb-6" style={{ color: 'var(--nh-text-secondary)' }}>Search for candidates across platforms</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <GlassCard onClick={() => setSearchType('github')} className="group cursor-pointer">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ background: 'var(--nh-primary-light)' }}>
                <Github className="w-7 h-7" style={{ color: '#24292e' }} />
              </div>
              <div>
                <h3 className="text-lg font-semibold" style={{ color: 'var(--nh-text)' }}>GitHub Talent Search</h3>
                <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>Find developers by repos, contributions & languages</p>
              </div>
            </div>
          </GlassCard>
          <GlassCard onClick={() => setSearchType('portal')} className="group cursor-pointer">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl flex items-center justify-center gradient-bg-subtle">
                <Globe className="w-7 h-7" style={{ color: 'var(--nh-primary)' }} />
              </div>
              <div>
                <h3 className="text-lg font-semibold" style={{ color: 'var(--nh-text)' }}>Job Portal Search</h3>
                <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>LinkedIn, Naukri, Internshala, Indeed</p>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    );
  }

  return (
    <div className="mb-8">
      <GlassCard>
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            {searchType === 'github'
              ? <Github className="w-6 h-6" />
              : <Globe className="w-6 h-6" style={{ color: 'var(--nh-primary)' }} />}
            <h2 className="text-xl font-bold" style={{ color: 'var(--nh-text)' }}>
              {searchType === 'github' ? 'GitHub' : 'Job Portal'} Talent Search
            </h2>
          </div>
          <Button variant="ghost" onClick={() => { setSearchType(null); setResults([]); }} className="rounded-xl text-sm"
            style={{ color: 'var(--nh-text-secondary)' }}>
            Change Source
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <Label className="text-sm font-medium mb-1.5 block" style={{ color: 'var(--nh-text)' }}>Role</Label>
            <Input value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. Full Stack Developer"
              className="rounded-xl" style={{ borderColor: 'var(--nh-border)', background: 'var(--nh-bg)', color: 'var(--nh-text)' }} />
          </div>
          <div>
            <Label className="text-sm font-medium mb-1.5 block" style={{ color: 'var(--nh-text)' }}>Skills</Label>
            <Input value={skills} onChange={(e) => setSkills(e.target.value)} placeholder="React, Node.js, Python"
              className="rounded-xl" style={{ borderColor: 'var(--nh-border)', background: 'var(--nh-bg)', color: 'var(--nh-text)' }} />
          </div>
          <div>
            <Label className="text-sm font-medium mb-1.5 block" style={{ color: 'var(--nh-text)' }}>Experience</Label>
            <Select value={expRange} onValueChange={setExpRange}>
              <SelectTrigger className="rounded-xl" style={{ borderColor: 'var(--nh-border)', background: 'var(--nh-bg)', color: 'var(--nh-text)' }}>
                <SelectValue placeholder="Any experience" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="0-2">0-2 years</SelectItem>
                <SelectItem value="2-5">2-5 years</SelectItem>
                <SelectItem value="5-10">5-10 years</SelectItem>
                <SelectItem value="10+">10+ years</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <Button onClick={handleSearch} disabled={searching} className="gradient-bg text-white rounded-xl">
          {searching ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Search className="w-4 h-4 mr-2" />}
          {searching ? 'Searching...' : 'Search Candidates'}
        </Button>
      </GlassCard>

      {results.length > 0 && (
        <div className="mt-6">
          <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--nh-text)' }}>
            Search Results ({results.length})
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {results.map((c, i) =>
              searchType === 'github'
                ? <GitHubCandidateCard key={c.id} candidate={c} index={i} onSchedule={onSchedule} onWaitlist={onWaitlist} />
                : <PortalCandidateCard key={c.id} candidate={c} index={i} onSchedule={onSchedule} onWaitlist={onWaitlist} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}