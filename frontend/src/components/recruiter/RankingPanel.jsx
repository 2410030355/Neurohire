import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ListOrdered, Loader2, ChevronDown, ChevronUp, Info, CheckCircle2, Clock, XCircle } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { jsonFetch } from '@/api/http';
import GlassCard from '@/components/shared/GlassCard';
import FitBadge from '@/components/shared/FitBadge';
import EmptyState from '@/components/shared/EmptyState';
import { logDecision, fmt } from './decisions';

const COMPONENTS = [
  { id: 'CS', label: 'Consistency' },
  { id: 'VS', label: 'Skill validation' },
  { id: 'LV', label: 'Learning velocity' },
];

const METHOD_LABEL = { gemini: 'Gemini embeddings', tfidf: 'TF-IDF fallback', none: 'not computed' };

function Cell({ value, strong = false }) {
  return (
    <td className={`py-2.5 pr-3 text-right tabular-nums ${strong ? 'font-semibold' : ''}`}
      style={{ color: value === null || value === undefined ? 'var(--nh-text-secondary)' : 'var(--nh-text)' }}>
      {fmt(value)}
    </td>
  );
}

function DecisionButtons({ row, rankingId, decided, onDecided }) {
  const send = async (decision) => {
    const log = await logDecision(row, decision, rankingId);
    if (log) {
      onDecided(row.candidate_id, decision, log.weight_update);
    } else {
      toast.error('Could not record the decision');
    }
  };
  const btn = (decision, Icon, color, title) => (
    <button onClick={() => send(decision)} title={title} disabled={decided === decision}
      className="p-1.5 rounded-lg hover:opacity-80 disabled:opacity-40"
      style={{ color, border: '1px solid var(--nh-border)' }}>
      <Icon className="w-3.5 h-3.5" />
    </button>
  );
  return (
    <div className="flex items-center gap-1 justify-end">
      {btn('hire', CheckCircle2, 'var(--nh-success)', 'Hire / shortlist')}
      {btn('waitlist', Clock, 'var(--nh-warning)', 'Waitlist')}
      {btn('reject', XCircle, 'var(--nh-danger)', 'Reject')}
    </div>
  );
}

export default function RankingPanel() {
  const [jd, setJd] = useState('');
  const [components, setComponents] = useState({ CS: true, VS: true, LV: true });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [open, setOpen] = useState(null);
  const [decisions, setDecisions] = useState({});
  const queryClient = useQueryClient();

  const words = jd.trim().split(/\s+/).filter(Boolean).length;

  const rank = async () => {
    if (jd.trim().length < 20) {
      toast.error('Paste a job description (at least a few sentences).');
      return;
    }
    setLoading(true);
    setDecisions({});
    try {
      const data = await jsonFetch('/api/rank/', {
        method: 'POST',
        body: JSON.stringify({
          job_description: jd.trim(),
          components: ['SS', ...Object.keys(components).filter(k => components[k])],
          top_k: 100,
        }),
      });
      setResult(data);
      if (!data?.results?.length) toast.info(data?.message || 'No stored résumés to rank yet.');
    } catch (err) {
      toast.error(err.message || 'Ranking failed');
    } finally {
      setLoading(false);
    }
  };

  const onDecided = (id, decision, update) => {
    setDecisions(d => ({ ...d, [id]: decision }));
    queryClient.invalidateQueries({ queryKey: ['ai-decisions'] });
    queryClient.invalidateQueries({ queryKey: ['feedback-weights'] });
    const moved = update?.updated
      ? ` Learned weight w_SS ${update.w_ss_before} → ${update.w_ss_after}.`
      : '';
    toast.success(`Recorded: ${decision}.${moved}`);
  };

  const ablation = Object.values(components).some(v => !v);

  return (
    <div className="space-y-6">
      <GlassCard hover={false}>
        <label className="text-sm font-medium mb-1.5 block" style={{ color: 'var(--nh-text)' }}>
          Job description
        </label>
        <textarea
          value={jd}
          onChange={e => setJd(e.target.value)}
          rows={7}
          placeholder="Paste the full job description. Every stored résumé is scored against it and ranked by final score."
          className="w-full px-4 py-3 rounded-xl text-sm resize-y"
          style={{ background: 'var(--nh-bg)', border: '1px solid var(--nh-border)', color: 'var(--nh-text)', lineHeight: 1.6 }}
        />
        <div className="flex flex-wrap items-center justify-between gap-3 mt-3">
          <div className="flex flex-wrap items-center gap-3 text-xs" style={{ color: 'var(--nh-text-secondary)' }}>
            <span>{words} words</span>
            <span className="opacity-60">|</span>
            <span>Analytical components:</span>
            {COMPONENTS.map(c => (
              <label key={c.id} className="flex items-center gap-1 cursor-pointer">
                <input type="checkbox" checked={components[c.id]}
                  onChange={e => setComponents(v => ({ ...v, [c.id]: e.target.checked }))} />
                {c.label}
              </label>
            ))}
          </div>
          <Button onClick={rank} disabled={loading} className="gradient-bg text-white rounded-xl">
            {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <ListOrdered className="w-4 h-4 mr-2" />}
            {loading ? 'Ranking…' : 'Rank candidates'}
          </Button>
        </div>
        {ablation && (
          <p className="text-xs mt-2" style={{ color: 'var(--nh-warning)' }}>
            Ablation run: AS uses only the ticked components (semantic similarity is always included).
          </p>
        )}
      </GlassCard>

      {result && result.results?.length === 0 && (
        <EmptyState title="Nothing to rank yet" description="Upload résumés in Resume Analysis first." action={null} />
      )}

      {result?.results?.length > 0 && (
        <GlassCard hover={false}>
          <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
            <div>
              <h3 className="font-semibold" style={{ color: 'var(--nh-text)' }}>
                {result.total_ranked} candidates ranked
              </h3>
              <p className="text-xs mt-1" style={{ color: 'var(--nh-text-secondary)' }}>
                FS = {result.weights?.SS}·SS + {result.weights?.AS}·AS ({result.weights_source || 'configured'} weights)
                {' · '}SS: {METHOD_LABEL[result.similarity_method] || result.similarity_method}
                {' · '}LV normalised over {result.lv_bounds?.n_with_lv ?? 0} candidates with dated history
              </p>
            </div>
            {result.similarity_method === 'tfidf' && (
              <span className="flex items-center gap-1 text-xs px-2 py-1 rounded-lg"
                style={{ background: 'rgba(212,165,116,0.15)', color: '#c4894a' }}>
                <Info className="w-3 h-3" /> Gemini unavailable — lexical fallback used for everyone
              </span>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--nh-border)' }}>
                  {['#', 'Candidate', 'FS', 'SS', 'CS', 'VS', 'LV', 'AS', 'Fit', 'Decision', ''].map((h, i) => (
                    <th key={h + i}
                      className={`py-2 pr-3 text-xs font-semibold uppercase tracking-wider ${i >= 2 && i <= 7 ? 'text-right' : 'text-left'}`}
                      style={{ color: 'var(--nh-text-secondary)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.results.map(r => (
                  <React.Fragment key={r.candidate_id}>
                    <tr style={{ borderBottom: '1px solid var(--nh-border-light)' }}>
                      <td className="py-2.5 pr-3 tabular-nums" style={{ color: 'var(--nh-text-secondary)' }}>{r.rank}</td>
                      <td className="py-2.5 pr-3 font-medium" style={{ color: 'var(--nh-text)' }}>
                        {r.name}
                        {decisions[r.candidate_id] && (
                          <span className="ml-2 text-[10px] uppercase" style={{ color: 'var(--nh-text-secondary)' }}>
                            {decisions[r.candidate_id]}
                          </span>
                        )}
                      </td>
                      <Cell value={r.final_score} strong />
                      <Cell value={r.semantic_score} />
                      <Cell value={r.consistency_score} />
                      <Cell value={r.skill_validation_score} />
                      <Cell value={r.lv_score} />
                      <Cell value={r.analytical_score} />
                      <td className="py-2.5 pr-3"><FitBadge level={r.final_fit} /></td>
                      <td className="py-2.5 pr-3">
                        <DecisionButtons row={r} rankingId={result.ranking_id}
                          decided={decisions[r.candidate_id]} onDecided={onDecided} />
                      </td>
                      <td className="py-2.5">
                        <button onClick={() => setOpen(open === r.candidate_id ? null : r.candidate_id)}
                          className="p-1" style={{ color: 'var(--nh-text-secondary)' }}>
                          {open === r.candidate_id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      </td>
                    </tr>
                    <AnimatePresence>
                      {open === r.candidate_id && (
                        <tr>
                          <td colSpan={11} className="p-0">
                            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                              <div className="p-4 grid md:grid-cols-2 gap-4 text-xs"
                                style={{ background: 'var(--nh-bg)', color: 'var(--nh-text)' }}>
                                <div>
                                  <p className="font-semibold mb-1" style={{ color: 'var(--nh-text-secondary)' }}>JD skills found</p>
                                  <p>{r.matched_skills?.length ? r.matched_skills.join(', ') : '—'}</p>
                                  <p className="font-semibold mt-3 mb-1" style={{ color: 'var(--nh-text-secondary)' }}>JD skills not in résumé</p>
                                  <p>{r.missing_skills?.length ? r.missing_skills.join(', ') : '—'}</p>
                                </div>
                                <div>
                                  <p className="font-semibold mb-1" style={{ color: 'var(--nh-text-secondary)' }}>Consistency flags</p>
                                  {r.consistency_flags?.length
                                    ? r.consistency_flags.map((f, i) => <p key={i}>• {f.message} (−{f.deduction})</p>)
                                    : <p>None triggered</p>}
                                  <p className="font-semibold mt-3 mb-1" style={{ color: 'var(--nh-text-secondary)' }}>Not available</p>
                                  <p>{r.missing_components?.length ? r.missing_components.join(', ') : 'All components computed'}</p>
                                  <p className="mt-3" style={{ color: 'var(--nh-text-secondary)' }}>
                                    Experience: {r.experience_years == null ? 'not dated' : `${r.experience_years} years`}
                                  </p>
                                </div>
                              </div>
                            </motion.div>
                          </td>
                        </tr>
                      )}
                    </AnimatePresence>
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] mt-3" style={{ color: 'var(--nh-text-secondary)' }}>
            Scores are heuristic indicators computed from résumé text; they do not verify competence.
            N/A means the component could not be computed and is left out of AS rather than counted as zero.
          </p>
        </GlassCard>
      )}
    </div>
  );
}
