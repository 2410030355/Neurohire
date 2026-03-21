import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload, Loader2, Target, TrendingUp, CheckCircle2,
  AlertCircle, Lightbulb, BookOpen, Zap, Award
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { API_BASE_URL } from '@/api/http';
import { toast } from 'sonner';
import GlassCard from '@/components/shared/GlassCard';

function ScoreCircle({ score, label, color, size = 90 }) {
  const r = (size - 12) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={size} height={size}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--nh-border)" strokeWidth={6} />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={6}
          strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={offset}
          transform={`rotate(-90 ${size/2} ${size/2})`}
          style={{ transition: 'stroke-dashoffset 1s ease' }} />
        <text x="50%" y="50%" textAnchor="middle" dy="0.35em"
          fontSize={size * 0.2} fontWeight="bold" fill="var(--nh-text)">{score}%</text>
      </svg>
      <p className="text-xs text-center font-medium" style={{ color: 'var(--nh-text-secondary)' }}>{label}</p>
    </div>
  );
}

function VelocityBadge({ level }) {
  const c = {
    High:   { bg: 'rgba(139,184,168,0.15)', text: '#5a9e8a', label: '🚀 High Learning Velocity' },
    Medium: { bg: 'rgba(212,165,116,0.15)', text: '#c4894a', label: '⚡ Medium Learning Velocity' },
    Low:    { bg: 'rgba(201,125,111,0.15)', text: '#c97d6f', label: '📈 Growing — Keep Learning' },
  }[level] || { bg: 'rgba(212,165,116,0.15)', text: '#c4894a', label: '⚡ Medium' };
  return (
    <span className="px-3 py-1 rounded-full text-sm font-semibold"
      style={{ background: c.bg, color: c.text }}>{c.label}</span>
  );
}

function SectionHeader({ icon: Icon, title, color }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${color}18` }}>
        <Icon className="w-4 h-4" style={{ color }} />
      </div>
      <h3 className="font-semibold text-base" style={{ color: 'var(--nh-text)' }}>{title}</h3>
    </div>
  );
}

export default function ResumeImprover() {
  const [file, setFile] = useState(null);
  const [targetRole, setTargetRole] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const analyze = async () => {
    if (!file) return toast.error('Please upload your resume');
    if (!targetRole.trim()) return toast.error('Please enter your target role');
    setAnalyzing(true);
    setError('');
    setResult(null);
    try {
      const formData = new FormData();
      formData.append('resume', file);
      formData.append('target_role', targetRole);
      const res = await fetch(`${API_BASE_URL}/api/seeker-resume/`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `Analysis failed (${res.status})`);
      }
      const data = await res.json();
      console.log('Seeker resume analysis result:', data); // debug
      setResult(data);
      toast.success('Resume analysis complete!');
    } catch (err) {
      setError(err.message || 'Analysis failed — please try again');
      toast.error(err.message || 'Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div>
      <GlassCard className="mb-6">
        <h2 className="text-xl font-bold mb-1" style={{ color: 'var(--nh-text)' }}>Resume Improvement Analyzer</h2>
        <p className="text-sm mb-6" style={{ color: 'var(--nh-text-secondary)' }}>
          Get personal feedback on what skills to learn, how to improve your resume, and where you stand for your target role.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <Label className="text-sm font-medium mb-1.5 block" style={{ color: 'var(--nh-text)' }}>Your Target Role</Label>
            <Input value={targetRole} onChange={e => setTargetRole(e.target.value)}
              placeholder="e.g. Frontend Developer" className="rounded-xl"
              style={{ borderColor: 'var(--nh-border)', background: 'var(--nh-bg)', color: 'var(--nh-text)' }} />
          </div>
          <div>
            <Label className="text-sm font-medium mb-1.5 block" style={{ color: 'var(--nh-text)' }}>Your Resume (PDF or DOCX)</Label>
            <label className="flex items-center gap-2 px-4 h-10 rounded-xl border cursor-pointer hover:opacity-80"
              style={{ borderColor: 'var(--nh-border)', background: 'var(--nh-bg)' }}>
              <Upload className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--nh-text-secondary)' }} />
              <span className="text-sm truncate" style={{ color: file ? 'var(--nh-text)' : 'var(--nh-text-secondary)' }}>
                {file ? file.name : 'Choose file...'}
              </span>
              <input type="file" accept=".pdf,.docx" onChange={e => setFile(e.target.files[0])} className="hidden" />
            </label>
          </div>
        </div>
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm mb-4">
            <AlertCircle className="w-4 h-4 shrink-0" /> {error}
          </div>
        )}
        <Button onClick={analyze} disabled={analyzing || !file} className="gradient-bg text-white rounded-xl">
          {analyzing
            ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />Analyzing your resume...</>
            : <><Target className="w-4 h-4 mr-2" />Analyze My Resume</>}
        </Button>
      </GlassCard>

      <AnimatePresence>
        {result && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">

            {/* Score overview */}
            <GlassCard>
              <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
                <div>
                  <h3 className="text-lg font-bold" style={{ color: 'var(--nh-text)' }}>Your Resume Report</h3>
                  <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>
                    Target: <span className="font-medium" style={{ color: 'var(--nh-primary)' }}>{result.target_role}</span>
                    {result.experience_years > 0 && ` • ${result.experience_years}y exp`}
                    {result.education && ` • ${result.education}`}
                  </p>
                </div>
                <VelocityBadge level={result.learning_velocity} />
              </div>
              <div className="flex items-center justify-around flex-wrap gap-6 mb-6">
                <ScoreCircle score={result.readiness_score} label="Overall Readiness" color="#8BB8A8" />
                <ScoreCircle score={result.resume_strength} label="Resume Strength" color="#D4A574" />
                <ScoreCircle score={result.role_alignment} label="Role Alignment" color="#7C9EC9" />
              </div>
              <div className="p-4 rounded-xl" style={{ background: 'var(--nh-bg)', border: '1px solid var(--nh-border)' }}>
                <p className="text-sm" style={{ color: 'var(--nh-text)' }}>
                  {result.readiness_score >= 75
                    ? ` You're well-prepared for ${result.target_role}! Polish and start applying.`
                    : result.readiness_score >= 50
                    ? ` You're on the right track for ${result.target_role}. A few targeted improvements will help a lot.`
                    : ` You have room to grow for ${result.target_role}. Focus on the skill gaps below and build projects.`}
                </p>
              </div>
            </GlassCard>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Strengths */}
              {result.strengths?.filter(s => s && s.trim()).length > 0 && (
                <GlassCard>
                  <SectionHeader icon={Award} title="What You're Doing Well" color="#8BB8A8" />
                  <div className="space-y-2">
                    {result.strengths.filter(s => s && s.trim()).map((s, i) => (
                      <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.07 }}
                        className="flex items-start gap-2.5 p-2.5 rounded-xl" style={{ background: 'var(--nh-bg)' }}>
                        <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0" style={{ color: '#8BB8A8' }} />
                        <span className="text-sm" style={{ color: 'var(--nh-text)' }}>{s}</span>
                      </motion.div>
                    ))}
                  </div>
                </GlassCard>
              )}

              {/* Skill gaps */}
              {result.skill_gaps?.filter(s => s && s.trim()).length > 0 && (
                <GlassCard>
                  <SectionHeader icon={BookOpen} title={`Skills to Learn for ${result.target_role}`} color="#D4A574" />
                  <p className="text-xs mb-3" style={{ color: 'var(--nh-text-secondary)' }}>
                    Commonly required but missing from your resume:
                  </p>
                  <div className="flex flex-wrap gap-2 mb-3">
                    {result.skill_gaps.filter(s => s && s.trim()).map((skill, i) => (
                      <motion.span key={i} initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: i * 0.06 }}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-medium"
                        style={{ background: 'rgba(212,165,116,0.12)', color: '#c4894a', border: '1px solid rgba(212,165,116,0.3)' }}>
                        <Zap className="w-3 h-3" />{skill}
                      </motion.span>
                    ))}
                  </div>
                  <p className="text-xs p-2 rounded-lg" style={{ color: 'var(--nh-text-secondary)', background: 'var(--nh-bg)' }}>
                     Build a small project using 2-3 of these and add it to your portfolio.
                  </p>
                </GlassCard>
              )}
            </div>

            {/* Current skills */}
            {result.current_skills?.length > 0 && (
              <GlassCard>
                <SectionHeader icon={CheckCircle2} title="Skills Found in Your Resume" color="#7C9EC9" />
                <div className="flex flex-wrap gap-2">
                  {result.current_skills.map((skill, i) => (
                    <span key={i} className="px-2.5 py-1 rounded-lg text-xs font-medium"
                      style={{ background: 'var(--nh-primary-light)', color: 'var(--nh-primary)' }}>
                      {skill}
                    </span>
                  ))}
                </div>
              </GlassCard>
            )}

            {/* Improvement tips */}
            {result.improvement_tips?.filter(t => t && t.trim()).length > 0 && (
              <GlassCard>
                <SectionHeader icon={Lightbulb} title="How to Improve Your Resume" color="#C97D6F" />
                <div className="space-y-3">
                  {result.improvement_tips.filter(t => t && t.trim()).map((tip, i) => (
                    <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.07 }}
                      className="flex items-start gap-3 p-3 rounded-xl"
                      style={{ background: 'var(--nh-bg)', border: '1px solid var(--nh-border)' }}>
                      <div className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
                        style={{ background: 'rgba(201,125,111,0.12)', minWidth: '1.5rem' }}>
                        <span className="text-xs font-bold" style={{ color: '#C97D6F' }}>{i + 1}</span>
                      </div>
                      <p className="text-sm leading-relaxed" style={{ color: 'var(--nh-text)' }}>{String(tip)}</p>
                    </motion.div>
                  ))}
                </div>
              </GlassCard>
            )}

            {/* Career summary */}
            {result.career_summary && (
              <GlassCard>
                <SectionHeader icon={TrendingUp} title="Your Career Trajectory" color="#8BB8A8" />
                <p className="text-sm leading-relaxed" style={{ color: 'var(--nh-text-secondary)' }}>
                  {result.career_summary}
                </p>
              </GlassCard>
            )}

          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}