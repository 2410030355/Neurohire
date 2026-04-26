import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageCircle, X, Send, Bot, Loader2 } from 'lucide-react';
import { API_BASE_URL } from '@/api/http';

// Renders **bold** and newlines from bot replies
function MdText({ text }) {
  return (
    <span>
      {text.split('\n').map((line, i) => {
        const parts = line.split(/(\*\*[^*]+\*\*)/g);
        return (
          <span key={i}>
            {parts.map((p, j) =>
              p.startsWith('**') && p.endsWith('**')
                ? <strong key={j}>{p.slice(2, -2)}</strong>
                : p
            )}
            {i < text.split('\n').length - 1 && <br />}
          </span>
        );
      })}
    </span>
  );
}

const QUICK = [
  'Show top candidates',
  'How does skill validation work?',
  'What is HAAR?',
  'How many candidates?',
];

export default function Chatbot() {
  const [open,     setOpen]     = useState(false);
  const [messages, setMessages] = useState([
    { role: 'bot', text: "Hi! I'm the NeuroHire assistant 👋\nAsk me about candidates, scores, features, or analytics." }
  ]);
  const [input,   setInput]   = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 150);
  }, [open]);

  const send = async (text) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;
    setInput('');
    setMessages(m => [...m, { role: 'user', text: msg }]);
    setLoading(true);

    // Build the full URL explicitly — no jsonFetch so we can log everything
    const url = `${API_BASE_URL}/api/chatbot/`;
    console.log('[Chatbot] POST →', url, { message: msg });

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // NO credentials: 'include' — chatbot is fully public, no session needed
        body: JSON.stringify({ message: msg }),
      });

      console.log('[Chatbot] response status:', res.status);
      const text_raw = await res.text();
      console.log('[Chatbot] raw response:', text_raw.slice(0, 300));

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}: ${text_raw.slice(0, 200)}`);
      }

      let data;
      try { data = JSON.parse(text_raw); }
      catch { throw new Error('Invalid JSON from server'); }

      setMessages(m => [...m, { role: 'bot', text: data.reply || 'No reply received.' }]);
    } catch (e) {
      console.error('[Chatbot] ERROR:', e);
      setMessages(m => [...m, {
        role: 'bot',
        text: `Error: ${e.message}\n\nCheck browser console (F12) for details.`
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* FAB */}
      <motion.button
        whileHover={{ scale: 1.08 }} whileTap={{ scale: 0.92 }}
        onClick={() => setOpen(v => !v)}
        className="fixed bottom-6 right-6 z-[300] w-14 h-14 rounded-full shadow-lg flex items-center justify-center"
        style={{ background: 'linear-gradient(135deg,#2DD4BF,#A78BFA)', boxShadow: '0 4px 20px rgba(45,212,191,0.4)' }}>
        {open ? <X className="w-6 h-6 text-white" /> : <MessageCircle className="w-6 h-6 text-white" />}
      </motion.button>

      {/* Window */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-24 right-6 z-[300] w-80 md:w-96 flex flex-col rounded-2xl overflow-hidden"
            style={{ height: '480px', background: 'var(--nh-card)', border: '1px solid var(--nh-border)', boxShadow: '0 20px 60px rgba(0,0,0,0.5)' }}>

            {/* Header */}
            <div className="flex items-center gap-3 px-4 py-3 border-b flex-shrink-0"
              style={{ borderColor: 'var(--nh-border)', background: 'linear-gradient(135deg,var(--nh-primary-light),var(--nh-secondary-light))' }}>
              <div className="w-8 h-8 rounded-full gradient-bg flex items-center justify-center">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div>
                <p className="text-sm font-semibold" style={{ color: 'var(--nh-text)' }}>NeuroHire Assistant</p>
                <p className="text-xs" style={{ color: 'var(--nh-text-secondary)' }}>MongoDB-powered</p>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 nh-scrollbar">
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className="max-w-[85%] px-3 py-2 text-sm leading-relaxed"
                    style={{
                      background: m.role === 'user' ? 'linear-gradient(135deg,#2DD4BF,#A78BFA)' : 'var(--nh-bg)',
                      color: m.role === 'user' ? '#fff' : 'var(--nh-text)',
                      borderRadius: m.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                    }}>
                    <MdText text={m.text} />
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="px-4 py-2 rounded-2xl" style={{ background: 'var(--nh-bg)' }}>
                    <Loader2 className="w-4 h-4 animate-spin" style={{ color: 'var(--nh-primary)' }} />
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Quick questions */}
            {messages.length <= 1 && (
              <div className="px-3 pb-2 flex-shrink-0 flex flex-wrap gap-1.5">
                {QUICK.map((q, i) => (
                  <button key={i} onClick={() => send(q)}
                    className="text-xs px-2.5 py-1 rounded-full transition-all"
                    style={{ background: 'var(--nh-primary-light)', color: 'var(--nh-primary)', border: '1px solid rgba(45,212,191,0.3)' }}>
                    {q}
                  </button>
                ))}
              </div>
            )}

            {/* Input */}
            <div className="flex items-center gap-2 px-3 py-3 border-t flex-shrink-0"
              style={{ borderColor: 'var(--nh-border)' }}>
              <input ref={inputRef}
                value={input} onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
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