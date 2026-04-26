import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileText, Loader2, Target, TrendingUp, AlertCircle, CheckCircle2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { API_BASE_URL } from '@/api/http';
import { toast } from 'sonner';
import GlassCard from '@/components/shared/GlassCard';
import ScoreRing from '@/components/shared/ScoreRing';
import FitBadge from '@/components/shared/FitBadge';

const ALLOWED_TYPES = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
const ALLOWED_EXTS  = ['.pdf', '.docx'];

export default function ResumeImprover() {
  const [file,       setFile]       = useState(null);
  const [targetRole, setTargetRole] = useState('');
  const [analyzing,  setAnalyzing]  = useState(false);
  const [result,     setResult]     = useState(null);
  const [error,      setError]      = useState('');

  const handleFile = (f) => {
    if (!f) return;
    const ext = '.' + f.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) {
      toast.error('Only PDF and DOCX files are supported');
      return;
    }
    setFile(f);
    setResult(null);
    setError('');
  };

  const analyze = async () => {
    if (!file)             return toast.error('Please upload your resume');
    if (!targetRole.trim()) return toast.error('Please enter a target role');

    setAnalyzing(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('resume', file);         // backend accepts both keys
      formData.append('target_role', targetRole.trim());

      const res = await fetch(`${API_BASE_URL}/api/seeker-resume/`, {
        method: 'POST',
        body: formData,
        credentials: 'include',
      });

      const text = await res.text();
      let data;
      try { data = JSON.parse(text); }
      catch { throw new Error(text || 'Server returned invalid response'); }

      if (!res.ok) throw new Error(data?.error || `Server error ${res.status}`);

      setResult(data);
      toast.success('Analysis complete!');
    } catch (e) {
      const msg = e.message || 'Analysis failed';
      setError(msg);
      toast.error(msg);
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div>
      <GlassCard className="mb-6">
        <h2 className="text-xl font-bold mb-1" style={{ color: 'var(--nh-text)' }}>
          Resume Improvement Analyzer
        </h2>
        <p className="text-sm mb-6" style={{ color: 'var(--nh-text-secondary)' }}>
          Get AI-powered feedback on your resume — supports PDF and DOCX
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <Label className="text-sm font-medium mb-1.5 block" style={{ color: 'var(--nh-text)' }}>
              Target Role <span style={{ color: 'var(--nh-danger)' }}>*</span>
            </Label>
            <Input value={targetRole} onChange={e => setTargetRole(e.target.value)}
              placeholder="e.g. Frontend Developer"
              className="rounded-xl"
              style={{ borderColor: 'var(--nh-border)', background: 'var(--nh-bg)', color: 'var(--nh-text)' }} />
          </div>
          <div>
            <Label className="text-sm font-medium mb-1.5 block" style={{ color: 'var(--nh-text)' }}>
              Resume (PDF or DOCX) <span style={{ color: 'var(--nh-danger)' }}>*</span>
            </Label>
            <label className="flex items-center gap-2 px-4 py-2 rounded-xl border cursor-pointer hover:opacity-80 transition-opacity"
              style={{ borderColor: file ? 'var(--nh-primary)' : 'var(--nh-border)', background: 'var(--nh-bg)' }}>
              <Upload className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--nh-text-secondary)' }} />
              <span className="text-sm truncate flex-1"
                style={{ color: file ? 'var(--nh-text)' : 'var(--nh-text-secondary)' }}>
                {file ? file.name : 'Choose PDF or DOCX...'}
              </span>
              {file && (
                <button onClick={e => { e.preventDefault(); setFile(null); setResult(null); }}
                  className="flex-shrink-0 hover:opacity-70">
                  <X className="w-4 h-4" style={{ color: 'var(--nh-text-secondary)' }} />
                </button>
              )}
              <input type="file" accept=".pdf,.docx"
                onChange={e => handleFile(e.target.files[0])} className="hidden" />
            </label>
          </div>
        </div>

        {error && (
          <div className="mb-4 px-4 py-3 rounded-xl text-sm flex items-center gap-2"
            style={{ background: 'rgba(248,113,113,0.1)', color: 'var(--nh-danger)' }}>
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}

        <Button onClick={analyze} disabled={analyzing || !file}
          className="gradient-bg text-white rounded-xl disabled:opacity-50">
          {analyzing
            ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />Analyzing {file?.name.split('.').pop().toUpperCase()}...</>
            : <><Target className="w-4 h-4 mr-2" />Analyze Resume</>}
        </Button>
      </GlassCard>

      <AnimatePresence>
        {result && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            {/* Scores */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <GlassCard className="flex items-center gap-4">
                <ScoreRing score={result.resume_strength_score || 0} size={64} />
                <div>
                  <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>Resume Strength</p>
                  <p className="text-lg font-bold" style={{ color: 'var(--nh-text)' }}>
                    {result.resume_strength_score || 0}/100
                  </p>
                </div>
              </GlassCard>
              <GlassCard className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-xl flex items-center justify-center gradient-bg-subtle">
                  <TrendingUp className="w-7 h-7" style={{ color: 'var(--nh-primary)' }} />
                </div>
                <div>
                  <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>Learning Velocity</p>
                  <FitBadge level={result.learning_velocity || 'Medium'} />
                </div>
              </GlassCard>
              <GlassCard className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-xl flex items-center justify-center"
                  style={{ background: 'var(--nh-primary-light)' }}>
                  <Target className="w-7 h-7" style={{ color: 'var(--nh-primary)' }} />
                </div>
                <div>
                  <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>Role Fit</p>
                  <FitBadge level={result.role_fit || result.final_fit || 'Medium'} />
                </div>
              </GlassCard>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Detected Skills */}
              {result.skills?.length > 0 && (
                <GlassCard>
                  <h3 className="font-semibold mb-3 flex items-center gap-2" style={{ color: 'var(--nh-text)' }}>
                    <CheckCircle2 className="w-5 h-5" style={{ color: 'var(--nh-primary)' }} />
                    Detected Skills ({result.skills.length})
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {result.skills.map((s, i) => (
                      <span key={i} className="text-xs px-2.5 py-1 rounded-full"
                        style={{ background: 'var(--nh-primary-light)', color: 'var(--nh-primary)' }}>
                        {s}
                      </span>
                    ))}
                  </div>
                </GlassCard>
              )}

              {/* Missing Skills */}
              {result.missing_skills?.length > 0 && (
                <GlassCard>
                  <h3 className="font-semibold mb-3 flex items-center gap-2" style={{ color: 'var(--nh-text)' }}>
                    <AlertCircle className="w-5 h-5 text-amber-500" /> Missing Skills
                  </h3>
                  <div className="space-y-2">
                    {result.missing_skills.map((s, i) => (
                      <div key={i} className="flex items-center gap-2 p-2 rounded-lg"
                        style={{ background: 'var(--nh-bg)' }}>
                        <div className="w-2 h-2 rounded-full bg-amber-400" />
                        <span className="text-sm" style={{ color: 'var(--nh-text)' }}>{s}</span>
                      </div>
                    ))}
                  </div>
                </GlassCard>
              )}

              {/* Improvement Tips */}
              {result.improvement_suggestions?.length > 0 && (
                <GlassCard>
                  <h3 className="font-semibold mb-3 flex items-center gap-2" style={{ color: 'var(--nh-text)' }}>
                    <CheckCircle2 className="w-5 h-5" style={{ color: 'var(--nh-primary)' }} />
                    Improvement Suggestions
                  </h3>
                  <div className="space-y-2">
                    {result.improvement_suggestions.map((s, i) => (
                      <div key={i} className="flex items-start gap-2 p-2 rounded-lg"
                        style={{ background: 'var(--nh-bg)' }}>
                        <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 gradient-bg-subtle">
                          <span className="text-xs font-bold" style={{ color: 'var(--nh-primary)' }}>{i + 1}</span>
                        </div>
                        <span className="text-sm" style={{ color: 'var(--nh-text)' }}>{s}</span>
                      </div>
                    ))}
                  </div>
                </GlassCard>
              )}

              {/* Strengths */}
              {result.strengths?.length > 0 && (
                <GlassCard>
                  <h3 className="font-semibold mb-3 flex items-center gap-2" style={{ color: 'var(--nh-text)' }}>
                    <CheckCircle2 className="w-5 h-5 text-green-500" /> Your Strengths
                  </h3>
                  <div className="space-y-2">
                    {result.strengths.map((s, i) => (
                      <div key={i} className="flex items-center gap-2 p-2 rounded-lg"
                        style={{ background: 'var(--nh-bg)' }}>
                        <div className="w-2 h-2 rounded-full bg-green-400" />
                        <span className="text-sm" style={{ color: 'var(--nh-text)' }}>{s}</span>
                      </div>
                    ))}
                  </div>
                </GlassCard>
              )}
            </div>

            {result.summary && (
              <GlassCard className="mt-6">
                <h3 className="font-semibold mb-2" style={{ color: 'var(--nh-text)' }}>Summary</h3>
                <p className="text-sm leading-relaxed" style={{ color: 'var(--nh-text-secondary)' }}>
                  {result.summary}
                </p>
              </GlassCard>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}