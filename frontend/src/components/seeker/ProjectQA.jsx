import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageSquare, Loader2, HelpCircle, ChevronDown, ChevronUp,
  Eye, EyeOff, CheckCircle2, Lightbulb, Code2, AlertCircle, RotateCcw
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { jsonFetch } from '@/api/http';
import { toast } from 'sonner';
import GlassCard from '@/components/shared/GlassCard';

// ── Difficulty config ─────────────────────────────────────────────────────
const DIFF = {
  Easy:   { bg: 'rgba(139,184,168,0.15)', text: '#5a9e8a' },
  Medium: { bg: 'rgba(212,165,116,0.15)', text: '#c4894a' },
  Hard:   { bg: 'rgba(201,125,111,0.15)', text: '#c97d6f' },
};

// ── Single Question Card ──────────────────────────────────────────────────
function QuestionCard({ q, index, revealed, onReveal }) {
  const dc = DIFF[q.difficulty] || DIFF.Medium;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
      className="rounded-2xl border overflow-hidden"
      style={{ background: 'var(--nh-card)', borderColor: 'var(--nh-border)' }}
    >
      {/* Question header */}
      <div className="p-4">
        <div className="flex items-start gap-3">
          {/* Number badge */}
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 font-bold text-sm"
            style={{ background: dc.bg, color: dc.text }}>
            {index + 1}
          </div>

          <div className="flex-1 min-w-0">
            {/* Difficulty + Topic */}
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <span className="px-2 py-0.5 rounded-full text-xs font-semibold"
                style={{ background: dc.bg, color: dc.text }}>
                {q.difficulty}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full"
                style={{ background: 'var(--nh-primary-light)', color: 'var(--nh-primary)' }}>
                {q.topic}
              </span>
            </div>

            {/* Question text */}
            <p className="font-semibold text-sm leading-relaxed mb-3"
              style={{ color: 'var(--nh-text)' }}>
              {q.question}
            </p>

            {/* Hint */}
            {q.hint && (
              <div className="flex items-start gap-2 p-2.5 rounded-xl mb-3"
                style={{ background: 'rgba(212,165,116,0.08)', border: '1px solid rgba(212,165,116,0.2)' }}>
                <Lightbulb className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style={{ color: '#c4894a' }} />
                <p className="text-xs italic" style={{ color: '#c4894a' }}>
                  <span className="font-semibold not-italic">Hint: </span>{q.hint}
                </p>
              </div>
            )}

            {/* Show / Hide Answer button */}
            <button
              onClick={() => onReveal(index)}
              className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-all hover:opacity-80"
              style={{
                background: revealed ? 'rgba(139,184,168,0.15)' : 'var(--nh-bg)',
                color: revealed ? '#5a9e8a' : 'var(--nh-text-secondary)',
                border: `1px solid ${revealed ? 'rgba(139,184,168,0.3)' : 'var(--nh-border)'}`,
              }}
            >
              {revealed
                ? <><EyeOff className="w-3.5 h-3.5" /> Hide Answer</>
                : <><Eye className="w-3.5 h-3.5" /> Show Answer</>}
            </button>
          </div>
        </div>
      </div>

      {/* Answer panel — slides in */}
      <AnimatePresence>
        {revealed && q.answer && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4">
              <div className="p-4 rounded-xl"
                style={{ background: 'var(--nh-bg)', border: '1px solid var(--nh-border)' }}>
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 className="w-4 h-4" style={{ color: '#5a9e8a' }} />
                  <span className="text-xs font-semibold uppercase tracking-wider"
                    style={{ color: '#5a9e8a' }}>
                    Model Answer
                  </span>
                </div>
                <p className="text-sm leading-relaxed" style={{ color: 'var(--nh-text)' }}>
                  {q.answer}
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ════════════════════════════════════════════════════════════════════════════
export default function ProjectQA() {
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [revealed, setRevealed] = useState({}); // { questionIndex: bool }
  const [showAll, setShowAll] = useState(false);

  const generate = async () => {
    if (!description.trim()) return toast.error('Please describe your project');
    setLoading(true);
    setError('');
    setResult(null);
    setRevealed({});
    setShowAll(false);
    try {
      const res = await jsonFetch('/api/project-qa/', {
        method: 'POST',
        body: JSON.stringify({ description }),
      });
      if (!res?.questions?.length) throw new Error('No questions generated');
      setResult(res);
      toast.success(`${res.questions.length} questions generated!`);
    } catch (err) {
      setError(err.message || 'Failed to generate questions');
      toast.error('Failed to generate questions');
    } finally {
      setLoading(false);
    }
  };

  const toggleReveal = (index) => {
    setRevealed(prev => ({ ...prev, [index]: !prev[index] }));
  };

  const toggleAll = () => {
    if (showAll) {
      setRevealed({});
    } else {
      const all = {};
      result?.questions?.forEach((_, i) => { all[i] = true; });
      setRevealed(all);
    }
    setShowAll(!showAll);
  };

  const reset = () => {
    setResult(null);
    setRevealed({});
    setShowAll(false);
    setDescription('');
  };

  return (
    <div>
      {/* ── Input Card ── */}
      <GlassCard className="mb-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center"
            style={{ background: 'var(--nh-primary-light)' }}>
            <MessageSquare className="w-6 h-6" style={{ color: 'var(--nh-primary)' }} />
          </div>
          <div>
            <h2 className="text-xl font-bold" style={{ color: 'var(--nh-text)' }}>
              Project Q&A Trainer
            </h2>
            <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>
              Describe your project → get interview questions + model answers to train with
            </p>
          </div>
        </div>

        <div className="p-3 rounded-xl mb-5 flex items-start gap-2"
          style={{ background: 'var(--nh-primary-light)', border: '1px solid var(--nh-border)' }}>
          <HelpCircle className="w-4 h-4 mt-0.5 flex-shrink-0" style={{ color: 'var(--nh-primary)' }} />
          <p className="text-xs" style={{ color: 'var(--nh-text)' }}>
            <strong>How to use:</strong> Read each question and try to answer it mentally or out loud first.
            Then click <strong>Show Answer</strong> to see a model answer and compare with yours.
          </p>
        </div>

        <div className="mb-4">
          <Label className="text-sm font-medium mb-1.5 block" style={{ color: 'var(--nh-text)' }}>
            Describe Your Project
          </Label>
          <Textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="e.g. Built a real-time chat app using React, Node.js, and WebSockets with JWT auth, Redis caching, and MongoDB. Users can create rooms, send messages, and see online presence..."
            className="rounded-xl min-h-[110px] text-sm"
            style={{ borderColor: 'var(--nh-border)', background: 'var(--nh-bg)', color: 'var(--nh-text)' }}
          />
          <p className="text-xs mt-1" style={{ color: 'var(--nh-text-secondary)' }}>
            Include tech stack, features, and any interesting challenges for better questions
          </p>
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm mb-4">
            <AlertCircle className="w-4 h-4 shrink-0" /> {error}
          </div>
        )}

        <div className="flex items-center gap-3">
          <Button onClick={generate} disabled={loading || !description.trim()}
            className="gradient-bg text-white rounded-xl">
            {loading
              ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />Generating...</>
              : <><HelpCircle className="w-4 h-4 mr-2" />Generate Q&A</>}
          </Button>
          {result && (
            <Button onClick={reset} variant="outline" className="rounded-xl"
              style={{ borderColor: 'var(--nh-border)', color: 'var(--nh-text-secondary)' }}>
              <RotateCcw className="w-4 h-4 mr-1.5" /> New Project
            </Button>
          )}
        </div>
      </GlassCard>

      {/* ── Results ── */}
      <AnimatePresence>
        {result && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            className="space-y-4">

            {/* Meta bar */}
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="px-3 py-1 rounded-full text-xs font-semibold"
                  style={{
                    background: result.overall_complexity === 'High'
                      ? 'rgba(201,125,111,0.15)' : result.overall_complexity === 'Medium'
                      ? 'rgba(212,165,116,0.15)' : 'rgba(139,184,168,0.15)',
                    color: result.overall_complexity === 'High' ? '#c97d6f'
                      : result.overall_complexity === 'Medium' ? '#c4894a' : '#5a9e8a',
                  }}>
                  {result.overall_complexity} Complexity
                </span>
                {result.topics_covered?.map((t, i) => (
                  <span key={i} className="px-2 py-0.5 rounded-lg text-xs"
                    style={{ background: 'var(--nh-primary-light)', color: 'var(--nh-primary)' }}>
                    {t}
                  </span>
                ))}
              </div>

              {/* Show all / Hide all */}
              <button onClick={toggleAll}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all"
                style={{ background: 'var(--nh-card)', border: '1px solid var(--nh-border)', color: 'var(--nh-text-secondary)' }}>
                {showAll
                  ? <><EyeOff className="w-3.5 h-3.5" /> Hide All Answers</>
                  : <><Eye className="w-3.5 h-3.5" /> Show All Answers</>}
              </button>
            </div>

            {/* Tech detected */}
            {result.tech_detected?.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                <Code2 className="w-3.5 h-3.5" style={{ color: 'var(--nh-text-secondary)' }} />
                <span className="text-xs" style={{ color: 'var(--nh-text-secondary)' }}>Detected:</span>
                {result.tech_detected.map((t, i) => (
                  <span key={i} className="px-2 py-0.5 rounded-md text-xs font-medium"
                    style={{ background: 'var(--nh-bg)', color: 'var(--nh-text-secondary)', border: '1px solid var(--nh-border)' }}>
                    {t}
                  </span>
                ))}
              </div>
            )}

            {/* Questions */}
            <div className="space-y-3">
              {result.questions.map((q, i) => (
                <QuestionCard
                  key={i}
                  q={q}
                  index={i}
                  revealed={!!revealed[i]}
                  onReveal={toggleReveal}
                />
              ))}
            </div>

            {/* Footer tip */}
            <p className="text-xs text-center pb-2" style={{ color: 'var(--nh-text-secondary)' }}>
              💡 Try answering each question out loud before revealing the answer — that's how you build real interview confidence.
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}