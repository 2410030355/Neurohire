import React from 'react';
import { motion } from 'framer-motion';
import {
  BarChart3, TrendingUp, AlertTriangle, CheckCircle,
  Brain, ShieldCheck, Zap, Target, Info, Scale
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { jsonFetch } from '@/api/http';
import GlassCard from '@/components/shared/GlassCard';
import EmptyState from '@/components/shared/EmptyState';
import LoadingSkeleton from '@/components/shared/LoadingSkeleton';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';

// ── Metric card ───────────────────────────────────────────────────────────
function MetricCard({ icon: Icon, label, value, subtitle, color, delay = 0 }) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
      transition={{ delay }} className="rounded-2xl p-4 border"
      style={{ background: 'var(--nh-card)', borderColor: 'var(--nh-border)', boxShadow: 'var(--nh-shadow-sm)' }}>
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: `${color}18` }}>
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider"
            style={{ color: 'var(--nh-text-secondary)' }}>{label}</p>
          <p className="text-2xl font-bold leading-tight" style={{ color: 'var(--nh-text)' }}>{value}</p>
        </div>
      </div>
      {subtitle && (
        <p className="text-xs leading-relaxed" style={{ color: 'var(--nh-text-secondary)' }}>{subtitle}</p>
      )}
    </motion.div>
  );
}

// ── Insight banner ────────────────────────────────────────────────────────
function InsightBanner({ type, message }) {
  const isWarning = type === 'warning';
  return (
    <div className="flex items-start gap-2.5 p-3 rounded-xl text-sm"
      style={{
        background: isWarning ? 'rgba(201,125,111,0.08)' : 'rgba(124,158,201,0.08)',
        border: `1px solid ${isWarning ? 'rgba(201,125,111,0.3)' : 'rgba(124,158,201,0.3)'}`,
      }}>
      {isWarning
        ? <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: '#c97d6f' }} />
        : <Info className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: '#7C9EC9' }} />}
      <span style={{ color: isWarning ? '#c97d6f' : '#7C9EC9' }}>{message}</span>
    </div>
  );
}

// ── Feedback weights (paper §IV.H) ────────────────────────────────────────
function FeedbackWeightsCard() {
  const { data } = useQuery({
    queryKey: ['feedback-weights'],
    queryFn: () => jsonFetch('/api/feedback/weights/'),
  });
  if (!data) return null;
  const pct = (v) => `${Math.round((v ?? 0) * 100)}%`;
  const Bar = ({ label, w }) => (
    <div className="mb-3">
      <div className="flex justify-between text-xs mb-1" style={{ color: 'var(--nh-text-secondary)' }}>
        <span>{label}</span><span>SS {pct(w?.w_ss)} · AS {pct(w?.w_as)}</span>
      </div>
      <div className="flex h-2 rounded-full overflow-hidden" style={{ background: 'var(--nh-border)' }}>
        <div style={{ width: pct(w?.w_ss), background: 'var(--nh-primary)' }} />
        <div style={{ width: pct(w?.w_as), background: '#9b7ec8' }} />
      </div>
    </div>
  );
  return (
    <GlassCard hover={false}>
      <h3 className="font-semibold mb-1 flex items-center gap-2" style={{ color: 'var(--nh-text)' }}>
        <Scale className="w-4 h-4" /> Recruiter-feedback weights
      </h3>
      <p className="text-xs mb-4" style={{ color: 'var(--nh-text-secondary)' }}>
        Each hire/reject moves w_SS by ±{data.learning_rate} toward the component (SS or AS) that dominated that
        candidate's score, within [{data.bounds?.join(', ')}]. Scoring uses{' '}
        <b>{data.adaptive_enabled ? 'the learned weights' : 'the configured weights'}</b>
        {data.adaptive_enabled ? '' : ' (set ADAPTIVE_WEIGHTS=1 to use the learned ones)'}.
      </p>
      <Bar label="Configured" w={data.configured} />
      <Bar label={`Learned (v${data.learned?.version ?? 0})`} w={data.learned} />
      {data.history?.length > 0 && (
        <div className="overflow-x-auto mt-2">
          <table className="w-full text-xs">
            <thead>
              <tr style={{ color: 'var(--nh-text-secondary)' }}>
                {['v', 'Decision', 'SS', 'AS', 's', 'w_SS'].map(h => <th key={h} className="text-left py-1 pr-3">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {data.history.slice(0, 8).map(h => (
                <tr key={h.version} style={{ color: 'var(--nh-text)', borderTop: '1px solid var(--nh-border-light)' }}>
                  <td className="py-1 pr-3">{h.version}</td>
                  <td className="py-1 pr-3 capitalize">{h.decision}</td>
                  <td className="py-1 pr-3">{h.semantic_score == null ? '—' : Math.round(h.semantic_score)}</td>
                  <td className="py-1 pr-3">{h.analytical_score == null ? '—' : Math.round(h.analytical_score)}</td>
                  <td className="py-1 pr-3">{h.s > 0 ? `+${h.s}` : h.s}</td>
                  <td className="py-1 pr-3">{h.before?.w_ss} → {h.after?.w_ss}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </GlassCard>
  );
}

// ════════════════════════════════════════════════════════════════════════════
export default function AIAnalytics() {
  const { data: rawLogs, isLoading } = useQuery({
    queryKey: ['ai-decisions'],
    queryFn: () => jsonFetch('/api/ai-decision-logs/'),
    initialData: [],
  });
  const { data: rawCandidates } = useQuery({
    queryKey: ['candidates'],
    queryFn: () => jsonFetch('/api/candidates/'),
    initialData: [],
  });

  const logs = Array.isArray(rawLogs) ? rawLogs : (rawLogs?.results || []);
  const allCandidates = Array.isArray(rawCandidates) ? rawCandidates : (rawCandidates?.results || []);
  const scored = allCandidates.filter(c => c.source === 'resume_upload' && c.consistency_score != null);

  if (isLoading) return <LoadingSkeleton rows={3} />;
  if (!logs.length && !scored.length) return (
    <EmptyState icon={BarChart3} title="No Data Yet"
      description="Analytics appear once résumés are analysed and recruiters make decisions."
      action={null} />
  );

  // ── Core stats (recruiter decisions) ────────────────────────────────────
  const total       = logs.length;
  const agreements  = logs.filter(l => l.is_agreement).length;
  const disagreements = total - agreements;
  const agreementRate = total ? Math.round((agreements / total) * 100) : 0;
  const pctOf = (n, d) => (d ? `${Math.round((n / d) * 100)}%` : '—');

  // ── Metrics (definitions match what is computed) ───────────────────────
  // HAAR — share of decisions where the recruiter matched the AI's fit band
  const HAAR = total ? `${agreementRate}%` : '—';
  // CDR — share of scored candidates with at least one consistency rule triggered
  const flagged = scored.filter(c => (c.consistency_flags?.length || 0) > 0 || c.consistency_score < 100).length;
  const CDR = pctOf(flagged, scored.length);
  // SVC — share of all detected skills that have action-verb evidence (Valid)
  const allSkills = scored.flatMap(c => c.validated_skills || []);
  const SVC = pctOf(allSkills.filter(v => v.status === 'Valid').length, allSkills.length);
  // LVC — share of scored candidates whose learning velocity could be computed
  const LVC = pctOf(scored.filter(c => c.lv_score != null).length, scored.length);

  // ── Disagreement insights (paper §IV.D) ────────────────────────────────
  const insights = [];

  // Insight 1: Recruiter consistently overriding High-fit AI recommendations
  const overriddenHighFit = logs.filter(
    l => l.ai_recommendation === 'hire' && l.recruiter_decision !== 'hire'
  ).length;
  if (overriddenHighFit >= 2) {
    insights.push({
      type: 'warning',
      message: `Recruiter overrode ${overriddenHighFit} AI "hire" recommendations — consider reviewing role match threshold or adding job description context.`,
    });
  }

  // Insight 2: Recruiter hiring candidates AI marked as low-fit
  const upgradedLowFit = logs.filter(
    l => l.ai_recommendation === 'reject' && l.recruiter_decision === 'hire'
  ).length;
  if (upgradedLowFit >= 1) {
    insights.push({
      type: 'info',
      message: `${upgradedLowFit} candidate(s) hired despite AI "reject" recommendation — system may be underweighting factors the recruiter values. These cases improve future calibration.`,
    });
  }

  // Insight 3: High agreement — system is well calibrated
  if (agreementRate >= 80 && total >= 5) {
    insights.push({
      type: 'info',
      message: `${agreementRate}% agreement rate across ${total} decisions — AI recommendations are well-aligned with recruiter judgment.`,
    });
  }

  // Insight 4: Low agreement — needs attention
  if (agreementRate < 50 && total >= 4) {
    insights.push({
      type: 'warning',
      message: `Agreement rate is ${agreementRate}% — significant divergence between AI and recruiter decisions. Review scoring weights or provide more specific role descriptions.`,
    });
  }

  // ── Chart data ──────────────────────────────────────────────────────────
  const pieData = [
    { name: 'Agreement',    value: agreements },
    { name: 'Override',     value: disagreements },
  ];
  const PIE_COLORS = ['#5a9e8a', '#c97d6f'];

  const decisionCounts = {};
  logs.forEach(l => {
    const key = l.recruiter_decision || 'unknown';
    decisionCounts[key] = (decisionCounts[key] || 0) + 1;
  });
  const barData = Object.entries(decisionCounts).map(([k, v]) => ({
    decision: k.charAt(0).toUpperCase() + k.slice(1),
    count: v,
  }));

  // Trend: group by date
  const byDate = {};
  logs.forEach(l => {
    const date = l.created_at ? l.created_at.slice(0, 10) : 'unknown';
    if (!byDate[date]) byDate[date] = { date, agreements: 0, overrides: 0 };
    if (l.is_agreement) byDate[date].agreements++;
    else byDate[date].overrides++;
  });
  const trendData = Object.values(byDate).sort((a, b) => a.date.localeCompare(b.date)).slice(-7);

  return (
    <div className="space-y-6">

      {/* ── Section: Evaluation Metrics (paper §V.C) ── */}
      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wider mb-3 flex items-center gap-2"
          style={{ color: 'var(--nh-text-secondary)' }}>
          <Target className="w-4 h-4" /> Evaluation Metrics
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard
            icon={CheckCircle} label="HAAR" value={HAAR}
            subtitle={`Human-AI agreement: decisions matching the AI's fit band (${total} decisions)`}
            color="#5a9e8a" delay={0}
          />
          <MetricCard
            icon={ShieldCheck} label="CDR" value={CDR}
            subtitle={`Consistency detection rate: candidates with ≥1 consistency rule triggered (${scored.length} scored)`}
            color="#7C9EC9" delay={0.05}
          />
          <MetricCard
            icon={Brain} label="SVC" value={SVC}
            subtitle={`Skill validation coverage: detected skills with action-verb evidence (${allSkills.length} skills)`}
            color="#c4894a" delay={0.1}
          />
          <MetricCard
            icon={Zap} label="LVC" value={LVC}
            subtitle="Learning-velocity coverage: candidates with enough dated history to compute LV"
            color="#9b7ec8" delay={0.15}
          />
        </div>
      </div>

      {/* ── Section: Summary stats ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <GlassCard onClick={undefined}>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center"
              style={{ background: 'rgba(90,158,138,0.12)' }}>
              <CheckCircle className="w-6 h-6" style={{ color: '#5a9e8a' }} />
            </div>
            <div>
              <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>Agreement Rate</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--nh-text)' }}>{agreementRate}%</p>
            </div>
          </div>
        </GlassCard>
        <GlassCard onClick={undefined}>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center"
              style={{ background: 'var(--nh-primary-light)' }}>
              <TrendingUp className="w-6 h-6" style={{ color: 'var(--nh-primary)' }} />
            </div>
            <div>
              <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>Total Decisions</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--nh-text)' }}>{total}</p>
            </div>
          </div>
        </GlassCard>
        <GlassCard onClick={undefined}>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center"
              style={{ background: 'rgba(201,125,111,0.10)' }}>
              <AlertTriangle className="w-6 h-6" style={{ color: '#c97d6f' }} />
            </div>
            <div>
              <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>Overrides</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--nh-text)' }}>{disagreements}</p>
            </div>
          </div>
        </GlassCard>
      </div>

      {/* ── Section: Disagreement insights (paper §IV.D) ── */}
      {insights.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wider mb-3 flex items-center gap-2"
            style={{ color: 'var(--nh-text-secondary)' }}>
            <Brain className="w-4 h-4" /> Human-AI Disagreement Insights
          </h3>
          <div className="space-y-2">
            {insights.map((ins, i) => (
              <InsightBanner key={i} type={ins.type} message={ins.message} />
            ))}
          </div>
        </div>
      )}

      {/* ── Section: Charts ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <GlassCard onClick={undefined}>
          <h3 className="font-semibold mb-4" style={{ color: 'var(--nh-text)' }}>
            AI vs Recruiter Agreement
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80}
                dataKey="value" paddingAngle={4}>
                {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-6 mt-2">
            {pieData.map((d, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ background: PIE_COLORS[i] }} />
                <span className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>
                  {d.name}: {d.value}
                </span>
              </div>
            ))}
          </div>
        </GlassCard>

        <GlassCard onClick={undefined}>
          <h3 className="font-semibold mb-4" style={{ color: 'var(--nh-text)' }}>
            Decision Distribution
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={barData}>
              <XAxis dataKey="decision" tick={{ fill: 'var(--nh-text-secondary)', fontSize: 12 }} />
              <YAxis tick={{ fill: 'var(--nh-text-secondary)', fontSize: 12 }} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="var(--nh-primary)" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </GlassCard>
      </div>

      <FeedbackWeightsCard />

      {/* ── Section: Decision log table ── */}
      <GlassCard onClick={undefined}>
        <h3 className="font-semibold mb-4" style={{ color: 'var(--nh-text)' }}>
          Recent Decisions
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: '1px solid var(--nh-border)' }}>
                {['Candidate', 'AI Says', 'Recruiter Decision', 'FS', 'Weight update', 'Outcome'].map(h => (
                  <th key={h} className="text-left py-2 pr-4 text-xs font-semibold uppercase tracking-wider"
                    style={{ color: 'var(--nh-text-secondary)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {logs.slice(0, 8).map((log, i) => {
                const agreed = log.is_agreement;
                return (
                  <tr key={i} style={{ borderBottom: '1px solid var(--nh-border-light)' }}>
                    <td className="py-2.5 pr-4 font-medium" style={{ color: 'var(--nh-text)' }}>
                      {log.candidate_name || '—'}
                    </td>
                    <td className="py-2.5 pr-4 capitalize" style={{ color: 'var(--nh-text-secondary)' }}>
                      {log.ai_recommendation || '—'}
                    </td>
                    <td className="py-2.5 pr-4 capitalize" style={{ color: 'var(--nh-text-secondary)' }}>
                      {log.recruiter_decision || '—'}
                    </td>
                    <td className="py-2.5 pr-4" style={{ color: 'var(--nh-text-secondary)' }}>
                      {log.final_score != null ? Math.round(log.final_score)
                        : log.role_match_score != null ? Math.round(log.role_match_score) : '—'}
                    </td>
                    <td className="py-2.5 pr-4 text-xs" style={{ color: 'var(--nh-text-secondary)' }}>
                      {log.weight_update?.updated
                        ? `w_SS ${log.weight_update.w_ss_before} → ${log.weight_update.w_ss_after}`
                        : (log.weight_update?.reason || '—')}
                    </td>
                    <td className="py-2.5">
                      <span className="px-2 py-0.5 rounded-lg text-xs font-medium"
                        style={{
                          background: agreed ? 'rgba(90,158,138,0.12)' : 'rgba(201,125,111,0.10)',
                          color: agreed ? '#5a9e8a' : '#c97d6f',
                        }}>
                        {agreed ? '✓ Agreed' : '↑ Override'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </GlassCard>

    </div>
  );
}