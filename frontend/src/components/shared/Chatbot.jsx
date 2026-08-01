import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageCircle, X, Send, Bot, Loader2, User, RotateCcw } from 'lucide-react';
import { API_BASE_URL } from '@/api/http';

// ── Render **bold** and \n from bot replies ──────────────────────────────
function MdText({ text }) {
  return (
    <span>
      {text.split('\n').map((line, i, arr) => {
        const parts = line.split(/(\*\*[^*]+\*\*)/g);
        return (
          <span key={i}>
            {parts.map((p, j) =>
              p.startsWith('**') && p.endsWith('**')
                ? <strong key={j}>{p.slice(2, -2)}</strong>
                : p
            )}
            {i < arr.length - 1 && <br />}
          </span>
        );
      })}
    </span>
  );
}

// ── Typing animation ─────────────────────────────────────────────────────
function TypingMessage({ text, onDone }) {
  const [displayed, setDisplayed] = useState('');
  const [done,      setDone]      = useState(false);
  const idx = useRef(0);

  useEffect(() => {
    if (!text) return;
    idx.current = 0;
    setDisplayed('');
    setDone(false);
    const speed = text.length > 200 ? 8 : 18;
    const timer = setInterval(() => {
      idx.current++;
      setDisplayed(text.slice(0, idx.current));
      if (idx.current >= text.length) {
        clearInterval(timer);
        setDone(true);
        onDone?.();
      }
    }, speed);
    return () => clearInterval(timer);
  }, [text]);

  return (
    <span>
      <MdText text={displayed} />
      {!done && <span className="animate-pulse">▍</span>}
    </span>
  );
}

const FOLLOW_UPS_BY_ROLE = {
  recruiter: ['Show top candidates', 'What is HAAR?', 'How does skill validation work?', 'How many candidates do we have?'],
  jobseeker: ['How can I improve my resume?', 'What skills am I missing?', 'Tips for mock interview', 'How is my readiness score calculated?'],
};

export default function Chatbot({ role = 'recruiter' }) {
  const [open,       setOpen]       = useState(false);
  const [messages,   setMessages]   = useState([]);
  const [input,      setInput]      = useState('');
  const [loading,    setLoading]    = useState(false);
  const [followUps,  setFollowUps]  = useState(FOLLOW_UPS_BY_ROLE[role] || FOLLOW_UPS_BY_ROLE.recruiter);
  const [typingIdx,  setTypingIdx]  = useState(null);
  const [histLoaded, setHistLoaded] = useState(false);
  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  // ── Scroll to bottom on new messages ──────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // ── Focus input when opened ────────────────────────────────────────────
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 150);
  }, [open]);

  // ── Load conversation history from MongoDB on first open ───────────────
  useEffect(() => {
    if (!open || histLoaded) return;
    setHistLoaded(true);
    fetch(`${API_BASE_URL}/api/chatbot/`, { credentials: 'include' })
      .then(r => r.json())
      .then(data => {
        if (data && typeof data === 'object' && Array.isArray(data.history) && data.history.length > 0) {
          setMessages(data.history.map(m => ({ ...m, typed: true })));
        } else {
          setMessages([{
            role: 'bot',
            text: role === 'recruiter'
              ? 'Hi! I\'m the NeuroHire assistant powered by MongoDB.\n\nAsk me about candidates, scores, analytics, or any feature.'
              : 'Hi! I\'m the NeuroHire assistant.\n\nAsk me about improving your resume, mock interviews, or job tips.',
            typed: true,
          }]);
        }
      })
      .catch(() => {
        setMessages([{
          role: 'bot',
          text: 'Hi! I\'m the NeuroHire assistant.\n\nAsk me anything about the platform.',
          typed: true,
        }]);
      });
  }, [open, histLoaded, role]);

  // ── Send message ───────────────────────────────────────────────────────
  const send = useCallback(async (text) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;
    setInput('');
    setFollowUps([]);

    setMessages(prev => [...prev, { role: 'user', text: msg, typed: true }]);
    setLoading(true);

    console.log('[Chatbot] POST', `${API_BASE_URL}/api/chatbot/`);
    try {
      const res = await fetch(`${API_BASE_URL}/api/chatbot/`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ message: msg, role }),
      });
      console.log('[Chatbot] status:', res.status);
      const raw = await res.text();
      if (!res.ok) throw new Error(`Server ${res.status}: ${raw.slice(0,100)}`);
      const data = JSON.parse(raw);

      setMessages(prev => {
        const next = [...prev, { role: 'bot', text: data.reply || 'No reply.', typed: false }];
        setTypingIdx(next.length - 1);
        return next;
      });
      setFollowUps(data.follow_ups || FOLLOW_UPS_BY_ROLE[role] || FOLLOW_UPS_BY_ROLE.recruiter);
    } catch (e) {
      console.error('[Chatbot] error:', e);
      setMessages(prev => [
        ...prev,
        { role: 'bot', text: `Error: ${e.message}\n\nCheck F12 console for details.`, typed: true }
      ]);
      setFollowUps(FOLLOW_UPS_BY_ROLE[role] || FOLLOW_UPS_BY_ROLE.recruiter);
    } finally {
      setLoading(false);
    }
  }, [input, loading]);

  const clearHistory = () => {
    setMessages([{
      role: 'bot',
      text: 'Chat cleared. How can I help you?',
      typed: true,
    }]);
    setFollowUps(FOLLOW_UPS_BY_ROLE[role] || FOLLOW_UPS_BY_ROLE.recruiter);
    setHistLoaded(false);
  };

  return (
    <>
      {/* ── FAB ── */}
      <motion.button
        whileHover={{ scale: 1.08 }} whileTap={{ scale: 0.92 }}
        onClick={() => setOpen(v => !v)}
        className="fixed bottom-6 right-6 z-[300] w-14 h-14 rounded-full flex items-center justify-center shadow-lg"
        style={{ background: 'linear-gradient(135deg,#2DD4BF,#A78BFA)', boxShadow: '0 4px 20px rgba(45,212,191,0.4)' }}
        aria-label="Open chatbot">
        <AnimatePresence mode="wait">
          {open
            ? <motion.div key="x"   initial={{rotate:-90,opacity:0}} animate={{rotate:0,opacity:1}} exit={{rotate:90,opacity:0}}><X className="w-6 h-6 text-white" /></motion.div>
            : <motion.div key="msg" initial={{rotate:90,opacity:0}}  animate={{rotate:0,opacity:1}} exit={{rotate:-90,opacity:0}}><MessageCircle className="w-6 h-6 text-white" /></motion.div>
          }
        </AnimatePresence>
      </motion.button>

      {/* ── Chat window ── */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 24, scale: 0.95 }}
            animate={{ opacity: 1, y: 0,  scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-24 right-6 z-[300] flex flex-col rounded-2xl overflow-hidden"
            style={{ width: 380, height: 520, background: 'var(--nh-card)', border: '1px solid var(--nh-border)', boxShadow: '0 20px 60px rgba(0,0,0,0.5)' }}>

            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b flex-shrink-0"
              style={{ borderColor: 'var(--nh-border)', background: 'linear-gradient(135deg,var(--nh-primary-light),var(--nh-secondary-light))' }}>
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full gradient-bg flex items-center justify-center">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div>
                  <p className="text-sm font-semibold" style={{ color: 'var(--nh-text)' }}>NeuroHire Assistant</p>
                  <p className="text-xs" style={{ color: 'var(--nh-text-secondary)' }}>MongoDB-powered</p>
                </div>
              </div>
              <button onClick={clearHistory} title="Clear history"
                className="p-1.5 rounded-lg opacity-60 hover:opacity-100 transition-opacity"
                style={{ color: 'var(--nh-text-secondary)' }}>
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 nh-scrollbar">
              {messages.length === 0 && (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" style={{ color: 'var(--nh-primary)' }} />
                    <p className="text-xs" style={{ color: 'var(--nh-text-secondary)' }}>Loading history...</p>
                  </div>
                </div>
              )}

              {messages.map((m, i) => (
                <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {m.role === 'bot' && (
                    <div className="w-6 h-6 rounded-full gradient-bg flex items-center justify-center flex-shrink-0 mt-1">
                      <Bot className="w-3 h-3 text-white" />
                    </div>
                  )}
                  <div className="max-w-[82%] px-3 py-2 text-sm leading-relaxed"
                    style={{
                      background: m.role === 'user' ? 'linear-gradient(135deg,#2DD4BF,#A78BFA)' : 'var(--nh-bg)',
                      color: m.role === 'user' ? '#fff' : 'var(--nh-text)',
                      borderRadius: m.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                    }}>
                    {m.role === 'bot' && !m.typed && i === typingIdx
                      ? <TypingMessage text={m.text} onDone={() => setMessages(prev => prev.map((x, j) => j === i ? {...x, typed: true} : x))} />
                      : <MdText text={m.text} />
                    }
                  </div>
                  {m.role === 'user' && (
                    <div className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-1"
                      style={{ background: 'var(--nh-secondary-light)' }}>
                      <User className="w-3 h-3" style={{ color: 'var(--nh-secondary)' }} />
                    </div>
                  )}
                </div>
              ))}

              {loading && (
                <div className="flex gap-2 justify-start">
                  <div className="w-6 h-6 rounded-full gradient-bg flex items-center justify-center flex-shrink-0">
                    <Bot className="w-3 h-3 text-white" />
                  </div>
                  <div className="px-4 py-3 rounded-2xl" style={{ background: 'var(--nh-bg)' }}>
                    <div className="flex gap-1">
                      {[0,1,2].map(i => (
                        <motion.div key={i} className="w-1.5 h-1.5 rounded-full"
                          style={{ background: 'var(--nh-primary)' }}
                          animate={{ y: [0,-4,0] }}
                          transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }} />
                      ))}
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Follow-up suggestions */}
            <AnimatePresence>
              {followUps.length > 0 && !loading && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="px-3 py-2 flex-shrink-0 flex flex-wrap gap-1.5 border-t"
                  style={{ borderColor: 'var(--nh-border)' }}>
                  {followUps.slice(0, 3).map((q, i) => (
                    <button key={i} onClick={() => send(q)}
                      className="text-xs px-2.5 py-1 rounded-full transition-all hover:opacity-80"
                      style={{ background: 'var(--nh-primary-light)', color: 'var(--nh-primary)', border: '1px solid rgba(45,212,191,0.25)' }}>
                      {q}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Input */}
            <div className="flex items-center gap-2 px-3 py-3 border-t flex-shrink-0"
              style={{ borderColor: 'var(--nh-border)' }}>
              <input ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && !loading && send()}
                placeholder="Ask anything..."
                className="flex-1 px-3 py-2 rounded-xl text-sm outline-none"
                style={{ background: 'var(--nh-bg)', border: '1px solid var(--nh-border)', color: 'var(--nh-text)' }} />
              <motion.button
                whileHover={{ scale: 1.08 }} whileTap={{ scale: 0.92 }}
                onClick={() => send()}
                disabled={!input.trim() || loading}
                className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 disabled:opacity-40"
                style={{ background: 'linear-gradient(135deg,#2DD4BF,#A78BFA)' }}>
                <Send className="w-4 h-4 text-white" />
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}