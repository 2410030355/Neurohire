import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronDown, ChevronUp, Calendar, Clock, User,
  CheckCircle2, AlertTriangle, HelpCircle, Info,
  Briefcase, GraduationCap, ExternalLink, Award
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useQueryClient } from '@tanstack/react-query';
import { jsonFetch } from '@/api/http';
import { toast } from 'sonner';
import ScoreRing from '@/components/shared/ScoreRing';
import FitBadge from '@/components/shared/FitBadge';

// ── Log recruiter decision vs AI recommendation ───────────────────────────
async function logDecision(candidate, recruiterDecision) {
  try {
    const fit = candidate?.final_fit || 'Low';
    const aiRec = fit === 'High' ? 'hire' : fit === 'Medium' ? 'waitlist' : 'reject';
    await jsonFetch('/api/ai-decision-logs/', {
      method: 'POST',
      body: JSON.stringify({
        candidate: candidate?.id || null,
        candidate_name: candidate?.name || 'Unknown',
        ai_recommendation: aiRec,
        recruiter_decision: recruiterDecision,
        role_match_score: candidate?.role_match_score || 0,
        consistency_score: candidate?.consistency_score || 0,
        notes: `Portal: ${candidate?.portal_source || 'direct'} | Fit: ${fit}`,
      }),
    });
  } catch (err) {
    console.warn('Decision log failed:', err);
  }
}

// ── Skill Validation Badge ────────────────────────────────────────────────
function SkillBadge({ skill, status }) {
  const config = {
    Valid:      { Icon: CheckCircle2, bg: 'rgba(139,184,168,0.15)', text: '#5a9e8a', border: 'rgba(139,184,168,0.3)' },
    Partial:    { Icon: AlertTriangle, bg: 'rgba(212,165,116,0.15)', text: '#c4894a', border: 'rgba(212,165,116,0.3)' },
    Unverified: { Icon: HelpCircle,   bg: 'rgba(180,180,180,0.10)', text: '#999',    border: 'rgba(180,180,180,0.2)' },
  }[status] || { Icon: HelpCircle, bg: 'rgba(180,180,180,0.10)', text: '#999', border: 'rgba(180,180,180,0.2)' };

  return (
    <span className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium"
      style={{ background: config.bg, color: config.text, border: `1px solid ${config.border}` }}>
      <config.Icon className="w-2.5 h-2.5 flex-shrink-0" />
      {skill}
    </span>
  );
}

// ── Consistency Flag ──────────────────────────────────────────────────────
function ConsistencyFlag({ flag }) {
  const isWarning = flag.type === 'warning';
  return (
    <div className="flex items-start gap-2 p-2.5 rounded-xl text-xs"
      style={{
        background: isWarning ? 'rgba(201,125,111,0.08)' : 'rgba(124,158,201,0.08)',
        border: `1px solid ${isWarning ? 'rgba(201,125,111,0.25)' : 'rgba(124,158,201,0.2)'}`,
      }}>
      {isWarning
        ? <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style={{ color: '#c97d6f' }} />
        : <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style={{ color: '#7C9EC9' }} />}
      <span style={{ color: isWarning ? '#c97d6f' : '#7C9EC9' }}>{flag.message}</span>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
export default function CandidateCard({ candidate, onSchedule, onWaitlist, index = 0 }) {
  const [expanded, setExpanded] = useState(false);
  const [waitlisting, setWaitlisting] = useState(false);
  const queryClient = useQueryClient();

  const safe = {
    name:      candidate?.name || 'Unknown',
    role:      candidate?.target_role || 'Candidate',
    exp:       candidate?.experience_years ?? 0,
    consistency: candidate?.consistency_score ?? 0,
    skills:    candidate?.skill_validation_score ?? 0,
    roleMatch: candidate?.role_match_score ?? 0,
    velocity:  candidate?.learning_velocity || 'Medium',
    fit:       candidate?.final_fit || 'Low',
    skillList: candidate?.skills || [],
    validated: candidate?.validated_skills || [],
    flags:     candidate?.consistency_flags || [],
  };

  const hasValidated = safe.validated.length > 0;

  const handleSchedule = async () => {
    await logDecision(candidate, 'hire');
    onSchedule?.(candidate);
  };

  const handleWaitlist = async () => {
    if (waitlisting) return;
    setWaitlisting(true);
    try {
      await logDecision(candidate, 'waitlist');
      await jsonFetch('/api/waitlist/', {
        method: 'POST',
        body: JSON.stringify({
          candidate_name: safe.name,
          candidate_role: safe.role,
          score: safe.roleMatch,
          notes: candidate?.explainability || '',
          status: 'waitlisted',
        }),
      });
      queryClient.invalidateQueries({ queryKey: ['waitlist'] });
      toast.success(`${safe.name} added to waitlist`);
      onWaitlist?.(candidate);
    } catch {
      toast.error('Failed to add to waitlist');
    } finally {
      setWaitlisting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="rounded-2xl overflow-hidden border transition-shadow hover:shadow-md"
      style={{ background: 'var(--nh-card)', borderColor: 'var(--nh-border)', boxShadow: 'var(--nh-shadow-sm)' }}
    >
      <div className="p-5">

        {/* ── Header ── */}
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ background: 'var(--nh-primary-light)' }}>
              <User className="w-6 h-6" style={{ color: 'var(--nh-primary)' }} />
            </div>
            <div className="min-w-0">
              <h3 className="font-semibold text-base truncate" style={{ color: 'var(--nh-text)' }}>
                {safe.name}
              </h3>
              <p className="text-sm truncate" style={{ color: 'var(--nh-text-secondary)' }}>
                {safe.role} • {safe.exp}y exp
                {candidate?.location ? ` • ${candidate.location}` : ''}
              </p>
            </div>
          </div>
          <FitBadge level={safe.fit} />
        </div>

        {/* ── Scores ── */}
        <div className="flex items-center justify-between gap-2 mb-4 flex-wrap">
          <ScoreRing score={safe.consistency} size={52} label="Consistency" color="var(--nh-success)" />
          <ScoreRing score={safe.skills}      size={52} label="Skill Val."  color="var(--nh-warning)" />
          <ScoreRing score={safe.roleMatch}   size={52} label="Role Match"  color="var(--nh-primary)" />
          <div className="flex flex-col items-center gap-1">
            <FitBadge level={safe.velocity} />
            <span className="text-xs" style={{ color: 'var(--nh-text-secondary)' }}>Velocity</span>
          </div>
        </div>

        {/* ── Top consistency warning (collapsed preview) ── */}
        {safe.flags.length > 0 && !expanded && (
          <div className="mb-3">
            <ConsistencyFlag flag={safe.flags[0]} />
          </div>
        )}

        {/* ── Skills with validation status ── */}
        {hasValidated ? (
          <>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {safe.validated.slice(0, 8).map((v, i) => (
                <SkillBadge key={i} skill={v.skill} status={v.status} />
              ))}
              {safe.validated.length > 8 && (
                <span className="px-2 py-1 text-xs" style={{ color: 'var(--nh-text-secondary)' }}>
                  +{safe.validated.length - 8} more
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 mb-4 text-xs" style={{ color: 'var(--nh-text-secondary)' }}>
              <span className="flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" style={{ color: '#5a9e8a' }} /> Verified by project
              </span>
              <span className="flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" style={{ color: '#c4894a' }} /> Cert only
              </span>
              <span className="flex items-center gap-1">
                <HelpCircle className="w-3 h-3" style={{ color: '#999' }} /> Unverified
              </span>
            </div>
          </>
        ) : safe.skillList.length > 0 ? (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {safe.skillList.slice(0, 6).map((skill, i) => (
              <span key={i} className="px-2.5 py-1 rounded-lg text-xs font-medium"
                style={{ background: 'var(--nh-primary-light)', color: 'var(--nh-primary)', border: '1px solid var(--nh-border-light)' }}>
                {skill}
              </span>
            ))}
          </div>
        ) : null}

        {/* ── Actions ── */}
        <div className="flex items-center gap-2 pt-1">
          <Button size="sm" onClick={handleSchedule}
            className="gradient-bg text-white rounded-xl flex-1 font-medium shadow-sm">
            <Calendar className="w-3.5 h-3.5 mr-1.5" /> Schedule
          </Button>
          <Button size="sm" variant="outline" onClick={handleWaitlist} disabled={waitlisting}
            className="rounded-xl flex-1 font-medium"
            style={{ borderColor: 'var(--nh-border)', color: 'var(--nh-text)' }}>
            <Clock className="w-3.5 h-3.5 mr-1.5" />
            {waitlisting ? 'Adding...' : 'Waitlist'}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setExpanded(!expanded)}
            className="rounded-xl px-2" style={{ color: 'var(--nh-text-secondary)' }}>
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </Button>
        </div>
      </div>

      {/* ── Expanded Detail Panel ── */}
      <AnimatePresence>
        {expanded && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="px-5 pb-5 pt-4 border-t space-y-4"
              style={{ borderColor: 'var(--nh-border-light)', background: 'var(--nh-bg)' }}>

              {/* Companies */}
              {candidate?.companies?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider mb-2 flex items-center gap-1.5"
                    style={{ color: 'var(--nh-text-secondary)' }}>
                    <Briefcase className="w-3 h-3" /> Work Experience
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {candidate.companies.map((c, i) => (
                      <span key={i} className="px-2.5 py-1 rounded-lg text-xs font-medium"
                        style={{ background: 'var(--nh-card)', border: '1px solid var(--nh-border)', color: 'var(--nh-text)' }}>
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Education */}
              {candidate?.education && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider mb-1 flex items-center gap-1.5"
                    style={{ color: 'var(--nh-text-secondary)' }}>
                    <GraduationCap className="w-3 h-3" /> Education
                  </h4>
                  <p className="text-sm" style={{ color: 'var(--nh-text)' }}>{candidate.education}</p>
                </div>
              )}

              {/* Projects */}
              {candidate?.projects?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider mb-2"
                    style={{ color: 'var(--nh-text-secondary)' }}>
                    Notable Projects
                  </h4>
                  <div className="space-y-1.5">
                    {candidate.projects.map((p, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <div className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0"
                          style={{ background: 'var(--nh-primary)' }} />
                        <p className="text-xs leading-relaxed" style={{ color: 'var(--nh-text)' }}>{p}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Certifications */}
              {candidate?.certifications?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider mb-2 flex items-center gap-1.5"
                    style={{ color: 'var(--nh-text-secondary)' }}>
                    <Award className="w-3 h-3" /> Certifications
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {candidate.certifications.map((cert, i) => (
                      <span key={i} className="px-2.5 py-1 rounded-lg text-xs font-medium"
                        style={{ background: 'rgba(139,184,168,0.12)', color: '#5a9e8a', border: '1px solid rgba(139,184,168,0.3)' }}>
                        {cert}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* All consistency flags */}
              {safe.flags.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider mb-2"
                    style={{ color: 'var(--nh-text-secondary)' }}>
                    Consistency Analysis
                  </h4>
                  <div className="space-y-2">
                    {safe.flags.map((flag, i) => (
                      <ConsistencyFlag key={i} flag={flag} />
                    ))}
                  </div>
                </div>
              )}

              {/* Explainability */}
              {candidate?.explainability && (
                <div className="p-3 rounded-xl"
                  style={{ background: 'var(--nh-card)', border: '1px solid var(--nh-border)' }}>
                  <h4 className="text-xs font-semibold uppercase tracking-wider mb-1"
                    style={{ color: 'var(--nh-primary)' }}>
                    Why This Rating
                  </h4>
                  <p className="text-xs leading-relaxed" style={{ color: 'var(--nh-text)' }}>
                    {candidate.explainability}
                  </p>
                </div>
              )}

              {/* Profile link */}
              {candidate?.profile_url && (
                <a href={candidate.profile_url} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-xs font-medium hover:opacity-80"
                  style={{ color: 'var(--nh-primary)' }}>
                  <ExternalLink className="w-3.5 h-3.5" />
                  View on {candidate.portal_source || 'portal'}
                </a>
              )}

            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}