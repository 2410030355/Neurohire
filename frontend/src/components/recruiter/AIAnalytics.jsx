import React from 'react';
import { motion } from 'framer-motion';
import {
  BarChart3, TrendingUp, AlertTriangle, CheckCircle,
  Brain, ShieldCheck, Zap, Target, Info
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

// ════════════════════════════════════════════════════════════════════════════
export default function AIAnalytics() {
  const { data: rawLogs, isLoading } = useQuery({
    queryKey: ['ai-decisions'],
    queryFn: () => jsonFetch('/api/ai-decision-logs/'),
    initialData: [],
  });

  const logs = Array.isArray(rawLogs) ? rawLogs : (rawLogs?.results || []);

  if (isLoading) return <LoadingSkeleton rows={3} />;
  if (!logs.length) return (
    <EmptyState icon={BarChart3} title="No Decision Data Yet"
      description="AI analytics will appear here as you review candidates and make hiring decisions."
      action={null} />
  );

  // ── Core stats ──────────────────────────────────────────────────────────
  const total       = logs.length;
  const agreements  = logs.filter(l => l.is_agreement).length;
  const disagreements = total - agreements;
  const agreementRate = Math.round((agreements / total) * 100);

  // ── Evaluation metrics (paper §V.C) ────────────────────────────────────
  // HAAR — Human-AI Agreement Ratio
  const HAAR = agreementRate;

  // CDR — Consistency Detection Rate
  // Proxy: % of candidates where consistency score < 80 (flags were raised)
  const lowConsistency = logs.filter(l => (l.consistency_score || 100) < 80).length;
  const CDR = total > 0 ? Math.round((lowConsistency / total) * 100) : 0;

  // SVC — Skill Validation Coverage
  // Proxy: % of decisions where role_match_score > 0 (skills were actually evaluated)
  const evaluated = logs.filter(l => (l.role_match_score || 0) > 0).length;
  const SVC = total > 0 ? Math.round((evaluated / total) * 100) : 0;

  // LVS — Learning Velocity Sensitivity
  // Proxy: % of decisions on High-velocity candidates that AI recommended hire
  const highVelocityHires = logs.filter(
    l => l.ai_recommendation === 'hire' && (l.role_match_score || 0) >= 70
  ).length;
  const LVS = total > 0 ? Math.round((highVelocityHires / total) * 100) : 0;

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
            icon={CheckCircle} label="HAAR" value={`${HAAR}%`}
            subtitle="Human-AI Agreement Ratio"
            color="#5a9e8a" delay={0}
          />
          <MetricCard
            icon={ShieldCheck} label="CDR" value={`${CDR}%`}
            subtitle="Consistency Detection Rate"
            color="#7C9EC9" delay={0.05}
          />
          <MetricCard
            icon={Brain} label="SVC" value={`${SVC}%`}
            subtitle="Skill Validation Coverage"
            color="#c4894a" delay={0.1}
          />
          <MetricCard
            icon={Zap} label="LVS" value={`${LVS}%`}
            subtitle="Learning Velocity Sensitivity"
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

      {/* ── Section: Decision log table ── */}
      <GlassCard onClick={undefined}>
        <h3 className="font-semibold mb-4" style={{ color: 'var(--nh-text)' }}>
          Recent Decisions
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: '1px solid var(--nh-border)' }}>
                {['Candidate', 'AI Says', 'Recruiter Decision', 'Match %', 'Outcome'].map(h => (
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
                      {log.role_match_score ? `${log.role_match_score}%` : '—'}
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