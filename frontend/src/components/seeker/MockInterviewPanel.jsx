import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mic, MicOff, Square, Play, Pause, Loader2,
  AlertTriangle, CheckCircle, RotateCcw, Radio, Brain
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { API_BASE_URL, jsonFetch } from '@/api/http';
import { toast } from 'sonner';
import GlassCard from '@/components/shared/GlassCard';
import ScoreRing from '@/components/shared/ScoreRing';

// ── Timer ─────────────────────────────────────────────────────────────────
function RecordingTimer({ isRecording }) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    if (!isRecording) { setSeconds(0); return; }
    const id = setInterval(() => setSeconds(s => s + 1), 1000);
    return () => clearInterval(id);
  }, [isRecording]);
  const mm = String(Math.floor(seconds / 60)).padStart(2, '0');
  const ss = String(seconds % 60).padStart(2, '0');
  return <span className="font-mono font-bold text-red-500">{mm}:{ss}</span>;
}

// ── Waveform ───────────────────────────────────────────────────────────────
function WaveformIndicator({ active }) {
  return (
    <div className="flex items-center gap-0.5 h-8">
      {[1,2,3,4,5,4,3,2,1].map((h, i) => (
        <motion.div key={i} className="w-1 rounded-full"
          style={{ background: active ? '#EF4444' : 'var(--nh-border)' }}
          animate={active
            ? { height: [`${h*5}px`, `${h*12}px`, `${h*5}px`] }
            : { height: '4px' }}
          transition={{ duration: 0.6, delay: i * 0.07, repeat: active ? Infinity : 0 }}
        />
      ))}
    </div>
  );
}

// ── Score Circle ───────────────────────────────────────────────────────────
function ScoreCircle({ score, label, color }) {
  const size = 72;
  const r = (size - 10) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--nh-border)" strokeWidth={5} />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={5}
          strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={offset}
          transform={`rotate(-90 ${size/2} ${size/2})`}
          style={{ transition: 'stroke-dashoffset 1s ease' }} />
        <text x="50%" y="50%" textAnchor="middle" dy="0.35em"
          fontSize={14} fontWeight="bold" fill="var(--nh-text)">{score}</text>
      </svg>
      <p className="text-xs text-center" style={{ color: 'var(--nh-text-secondary)' }}>{label}</p>
    </div>
  );
}

export default function MockInterviewPanel() {
  const [role, setRole] = useState('');
  const [stage, setStage] = useState('setup'); // setup | interview | results
  const [questions, setQuestions] = useState([]);
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');

  // Recording
  const [isRecording, setIsRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [speechSupported, setSpeechSupported] = useState(true);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const audioRef = useRef(null);
  const recognitionRef = useRef(null);
  const finalTranscriptRef = useRef('');

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) setSpeechSupported(false);
  }, []);

  // ── Speech recognition ──────────────────────────────────────────────────
  const startSpeechRecognition = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return;
    finalTranscriptRef.current = '';
    const rec = new SR();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = 'en-US';
    rec.onresult = (e) => {
      let interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) {
          finalTranscriptRef.current += e.results[i][0].transcript + ' ';
        } else {
          interim += e.results[i][0].transcript;
        }
      }
      setTranscript(finalTranscriptRef.current + interim);
    };
    rec.onerror = (e) => {
      if (e.error !== 'no-speech') console.warn('Speech recognition error:', e.error);
    };
    recognitionRef.current = rec;
    try { rec.start(); } catch (e) { console.warn('SR start error:', e); }
  };

  // ── Recording ───────────────────────────────────────────────────────────
  const startRecording = async () => {
    setError('');
    setAudioUrl(null);
    setTranscript('');
    chunksRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      mediaRecorderRef.current = mr;
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setAudioUrl(URL.createObjectURL(blob));
      };
      mr.start(100); // collect every 100ms
      setIsRecording(true);
      startSpeechRecognition();
    } catch (err) {
      setError('Microphone access denied. Please allow microphone permission and try again.');
      toast.error('Microphone access denied');
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    recognitionRef.current?.stop();
    setIsRecording(false);
    // Give speech recognition a moment to finalize
    setTimeout(() => {
      setTranscript(finalTranscriptRef.current.trim() || transcript.trim());
    }, 500);
  };

  const togglePlayback = () => {
    if (!audioRef.current) return;
    if (isPlaying) { audioRef.current.pause(); setIsPlaying(false); }
    else { audioRef.current.play(); setIsPlaying(true); }
  };

  // ── Start interview ─────────────────────────────────────────────────────
  const startInterview = async () => {
    if (!role.trim()) return toast.error('Please specify a role');
    setLoading(true);
    setError('');
    try {
      const res = await jsonFetch('/api/mock-interview/start/', {
        method: 'POST',
        body: JSON.stringify({ role }),
      });
      if (!res?.questions?.length) throw new Error('No questions returned');
      setQuestions(res.questions);
      setStage('interview');
      setCurrentQ(0);
      setAnswers([]);
      setAudioUrl(null);
      setTranscript('');
    } catch (err) {
      setError(err.message || 'Failed to start interview');
      toast.error('Failed to start interview');
    } finally {
      setLoading(false);
    }
  };

  // ── Submit answer ───────────────────────────────────────────────────────
  const submitAnswer = async () => {
    const finalText = finalTranscriptRef.current.trim() || transcript.trim();

    if (!audioUrl && !finalText) {
      return toast.error('Please record your answer first');
    }

    // If we have audio but no transcript, use placeholder
    const answerTranscript = finalText || '(Audio recorded but no transcript — answer not detected)';

    const newAnswer = {
      question: questions[currentQ]?.question || `Question ${currentQ + 1}`,
      transcript: answerTranscript,
    };
    const newAnswers = [...answers, newAnswer];
    setAnswers(newAnswers);
    setAudioUrl(null);
    setTranscript('');
    finalTranscriptRef.current = '';

    if (currentQ < questions.length - 1) {
      setCurrentQ(currentQ + 1);
    } else {
      await analyzeInterview(newAnswers);
    }
  };

  // ── Analyze ─────────────────────────────────────────────────────────────
  const analyzeInterview = async (allAnswers) => {
    setLoading(true);
    setStage('results');
    setError('');
    try {
      const analysis = await jsonFetch('/api/mock-interview/analyze/', {
        method: 'POST',
        body: JSON.stringify({ role, answers: allAnswers }),
      });
      // Save session
      try {
        await jsonFetch('/api/mock-interviews/', {
          method: 'POST',
          body: JSON.stringify({
            role,
            overall_confidence: analysis.overall_confidence,
            overall_clarity: analysis.overall_clarity,
            total_filler_words: analysis.filler_word_estimate,
            avg_speaking_pace: analysis.speaking_pace,
            improvements: analysis.improvements,
            status: 'completed',
          }),
        });
      } catch {} // non-critical
      setResults(analysis);
    } catch (err) {
      setError(err.message || 'Analysis failed');
      toast.error('Analysis failed — please try again');
    } finally {
      setLoading(false);
    }
  };

  const resetAll = () => {
    setStage('setup'); setResults(null); setQuestions([]);
    setAnswers([]); setAudioUrl(null); setTranscript('');
    setCurrentQ(0); setError(''); finalTranscriptRef.current = '';
  };

  // ════════════════════════════════════════════════════════════════════════
  // SETUP
  // ════════════════════════════════════════════════════════════════════════
  if (stage === 'setup') return (
    <GlassCard>
      <div className="flex items-center gap-3 mb-6">
        <div className="w-12 h-12 rounded-xl gradient-bg flex items-center justify-center">
          <Mic className="w-6 h-6 text-white" />
        </div>
        <div>
          <h2 className="text-xl font-bold" style={{ color: 'var(--nh-text)' }}>Audio Mock Interview</h2>
          <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>Voice-based practice with AI analysis</p>
        </div>
      </div>

      <div className="p-4 rounded-xl mb-5 flex items-start gap-3"
        style={{ background: 'var(--nh-primary-light)', border: '1px solid var(--nh-border)' }}>
        <Radio className="w-5 h-5 mt-0.5 flex-shrink-0" style={{ color: 'var(--nh-primary)' }} />
        <div className="text-sm" style={{ color: 'var(--nh-text)' }}>
          <p><strong>How it works:</strong> You'll get 6 role-specific questions. Record your spoken answer for each one. After all questions, AI analyses your transcript for confidence, clarity, filler words, and technical knowledge.</p>
          {!speechSupported && (
            <p className="mt-2 text-amber-600 font-medium">⚠️ Your browser doesn't support speech-to-text. Audio will be recorded but no transcript will be generated. Use Chrome for best results.</p>
          )}
        </div>
      </div>

      <div className="mb-5">
        <Label className="text-sm font-medium mb-1.5 block" style={{ color: 'var(--nh-text)' }}>
          What role are you preparing for?
        </Label>
        <Input value={role} onChange={e => setRole(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && startInterview()}
          placeholder="e.g. Backend Developer, Data Scientist, DevOps Engineer"
          className="rounded-xl"
          style={{ borderColor: 'var(--nh-border)', background: 'var(--nh-bg)', color: 'var(--nh-text)' }} />
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm mb-4">
          <AlertTriangle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}

      <Button onClick={startInterview} disabled={loading || !role.trim()}
        className="gradient-bg text-white rounded-xl">
        {loading
          ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />Generating questions...</>
          : <><Mic className="w-4 h-4 mr-2" />Start Audio Interview</>}
      </Button>
    </GlassCard>
  );

  // ════════════════════════════════════════════════════════════════════════
  // INTERVIEW
  // ════════════════════════════════════════════════════════════════════════
  if (stage === 'interview') {
    const q = questions[currentQ];
    return (
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xl font-bold" style={{ color: 'var(--nh-text)' }}>
            Mock Interview — {role}
          </h2>
          <span className="text-sm font-medium px-3 py-1 rounded-full"
            style={{ background: 'var(--nh-primary-light)', color: 'var(--nh-primary)' }}>
            Q {currentQ + 1} / {questions.length}
          </span>
        </div>

        {/* Progress */}
        <div className="w-full h-1.5 rounded-full mb-6" style={{ background: 'var(--nh-border)' }}>
          <motion.div className="h-1.5 rounded-full gradient-bg"
            animate={{ width: `${((currentQ + 1) / questions.length) * 100}%` }} />
        </div>

        <GlassCard>
          {/* Difficulty + Topic */}
          {q && (
            <div className="flex items-center gap-2 mb-4">
              <span className="px-2 py-0.5 rounded-lg text-xs font-semibold" style={{
                background: q.difficulty === 'Hard' ? '#EF444415' : q.difficulty === 'Medium' ? '#F59E0B15' : '#10B98115',
                color: q.difficulty === 'Hard' ? '#EF4444' : q.difficulty === 'Medium' ? '#F59E0B' : '#10B981',
              }}>{q.difficulty}</span>
              <span className="text-xs px-2 py-0.5 rounded-lg"
                style={{ background: 'var(--nh-primary-light)', color: 'var(--nh-primary)' }}>
                {q.topic}
              </span>
            </div>
          )}

          {/* Question */}
          <div className="p-4 rounded-xl mb-6"
            style={{ background: 'var(--nh-bg)', border: '1px solid var(--nh-border)' }}>
            <p className="text-base font-semibold leading-relaxed" style={{ color: 'var(--nh-text)' }}>
              {q?.question}
            </p>
          </div>

          {/* Recording UI */}
          <div className="flex flex-col items-center py-2">
            <WaveformIndicator active={isRecording} />

            {isRecording && (
              <div className="flex items-center gap-2 my-3">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                <RecordingTimer isRecording={isRecording} />
                <span className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>Recording...</span>
              </div>
            )}

            {/* Mic / Stop button */}
            {!audioUrl && (
              <button
                onClick={isRecording ? stopRecording : startRecording}
                style={{
                  marginTop: '12px',
                  width: '64px',
                  height: '64px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 4px 14px rgba(0,0,0,0.15)',
                  border: 'none',
                  cursor: 'pointer',
                  background: isRecording
                    ? '#EF4444'
                    : 'linear-gradient(135deg, #6B9E96 0%, #4a7c74 100%)',
                  transition: 'all 0.2s ease',
                }}
              >
                {isRecording
                  ? <Square className="w-6 h-6" style={{ color: '#fff' }} />
                  : <Mic className="w-7 h-7" style={{ color: '#fff' }} />}
              </button>
            )}
            <p className="text-xs mt-2" style={{ color: 'var(--nh-text-secondary)' }}>
              {isRecording ? 'Click to stop recording' : !audioUrl ? 'Click mic to start recording' : ''}
            </p>

            {/* Playback */}
            {audioUrl && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                className="w-full mt-4 space-y-3">
                <audio ref={audioRef} src={audioUrl} onEnded={() => setIsPlaying(false)} />

                <div className="flex items-center gap-3 p-3 rounded-xl"
                  style={{ background: 'var(--nh-bg)', border: '1px solid var(--nh-border)' }}>
                  <Button size="sm" onClick={togglePlayback} variant="outline" className="rounded-xl">
                    {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  </Button>
                  <div className="flex-1">
                    <WaveformIndicator active={isPlaying} />
                  </div>
                  <Button size="sm" variant="ghost" className="rounded-xl"
                    onClick={() => { setAudioUrl(null); setTranscript(''); finalTranscriptRef.current = ''; }}>
                    <RotateCcw className="w-4 h-4 mr-1" /> Re-record
                  </Button>
                </div>

                {/* Transcript preview */}
                {transcript ? (
                  <div className="p-3 rounded-xl"
                    style={{ background: 'var(--nh-bg)', border: '1px solid var(--nh-border)' }}>
                    <p className="text-xs font-medium mb-1" style={{ color: 'var(--nh-text-secondary)' }}>
                      Transcript detected:
                    </p>
                    <p className="text-sm" style={{ color: 'var(--nh-text)' }}>{transcript}</p>
                  </div>
                ) : (
                  <div className="p-3 rounded-xl text-sm"
                    style={{ background: '#FEF9C3', border: '1px solid #FDE047', color: '#92400E' }}>
                    ⚠️ No transcript detected. Make sure you spoke clearly. The answer will still be submitted.
                  </div>
                )}

                <Button onClick={submitAnswer} className="gradient-bg text-white rounded-xl w-full">
                  {currentQ < questions.length - 1 ? '✓ Submit & Next Question' : '✓ Submit & Analyze Interview'}
                </Button>
              </motion.div>
            )}
          </div>
        </GlassCard>
      </div>
    );
  }

  // ════════════════════════════════════════════════════════════════════════
  // RESULTS
  // ════════════════════════════════════════════════════════════════════════
  return (
    <div>
      <h2 className="text-xl font-bold mb-6" style={{ color: 'var(--nh-text)' }}>
        Interview Analysis
      </h2>

      {loading ? (
        <GlassCard className="flex flex-col items-center justify-center py-14 gap-4">
          <Loader2 className="w-10 h-10 animate-spin" style={{ color: 'var(--nh-primary)' }} />
          <p className="text-base font-medium" style={{ color: 'var(--nh-text)' }}>
            Analysing your responses...
          </p>
          <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>
            Evaluating confidence, clarity, filler words and technical knowledge
          </p>
        </GlassCard>
      ) : error ? (
        <GlassCard className="text-center py-10">
          <AlertTriangle className="w-10 h-10 mx-auto mb-3 text-red-400" />
          <p className="text-red-600 mb-4">{error}</p>
          <Button onClick={resetAll} className="gradient-bg text-white rounded-xl">Try Again</Button>
        </GlassCard>
      ) : results && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">

          {/* Score cards */}
          <GlassCard>
            <h3 className="font-semibold mb-5" style={{ color: 'var(--nh-text)' }}>Overall Performance</h3>
            <div className="flex items-center justify-around flex-wrap gap-4">
              <ScoreCircle score={results.overall_confidence} label="Confidence" color="#8BB8A8" />
              <ScoreCircle score={results.overall_clarity} label="Clarity" color="#D4A574" />
              <ScoreCircle score={results.knowledge_relevance} label="Relevance" color="#7C9EC9" />
              <ScoreCircle score={results.energy_level} label="Energy" color="#C97D6F" />
            </div>
          </GlassCard>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-4">
            <GlassCard className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ background: 'rgba(212,165,116,0.15)' }}>
                <Mic className="w-5 h-5" style={{ color: '#D4A574' }} />
              </div>
              <div>
                <p className="text-xs" style={{ color: 'var(--nh-text-secondary)' }}>Speaking Pace</p>
                <p className="font-semibold text-sm" style={{ color: 'var(--nh-text)' }}>
                  {results.speaking_pace}
                </p>
              </div>
            </GlassCard>
            <GlassCard className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ background: 'rgba(201,125,111,0.15)' }}>
                <MicOff className="w-5 h-5" style={{ color: '#C97D6F' }} />
              </div>
              <div>
                <p className="text-xs" style={{ color: 'var(--nh-text-secondary)' }}>Filler Words</p>
                <p className="font-semibold text-sm" style={{ color: 'var(--nh-text)' }}>
                  {results.filler_word_estimate} detected
                </p>
              </div>
            </GlassCard>
          </div>

          {/* Strengths + Improvements */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {results.strengths?.filter(s => s).length > 0 && (
              <GlassCard>
                <h3 className="font-semibold mb-3 flex items-center gap-2" style={{ color: 'var(--nh-text)' }}>
                  <CheckCircle className="w-5 h-5 text-emerald-500" /> Strengths
                </h3>
                <div className="space-y-2">
                  {results.strengths.filter(s => s).map((s, i) => (
                    <div key={i} className="flex items-start gap-2 p-2.5 rounded-xl"
                      style={{ background: 'var(--nh-bg)' }}>
                      <div className="w-2 h-2 rounded-full bg-emerald-400 mt-1.5 flex-shrink-0" />
                      <span className="text-sm" style={{ color: 'var(--nh-text)' }}>{s}</span>
                    </div>
                  ))}
                </div>
              </GlassCard>
            )}
            {results.improvements?.filter(s => s).length > 0 && (
              <GlassCard>
                <h3 className="font-semibold mb-3 flex items-center gap-2" style={{ color: 'var(--nh-text)' }}>
                  <AlertTriangle className="w-5 h-5 text-amber-500" /> What to Improve
                </h3>
                <div className="space-y-2">
                  {results.improvements.filter(s => s).map((s, i) => (
                    <div key={i} className="flex items-start gap-2 p-2.5 rounded-xl"
                      style={{ background: 'var(--nh-bg)' }}>
                      <div className="w-2 h-2 rounded-full bg-amber-400 mt-1.5 flex-shrink-0" />
                      <span className="text-sm" style={{ color: 'var(--nh-text)' }}>{s}</span>
                    </div>
                  ))}
                </div>
              </GlassCard>
            )}
          </div>

          {/* Per-question breakdown */}
          {results.per_question?.length > 0 && (
            <GlassCard>
              <h3 className="font-semibold mb-4" style={{ color: 'var(--nh-text)' }}>
                Per-Question Breakdown
              </h3>
              <div className="space-y-3">
                {results.per_question.map((pq, i) => (
                  <div key={i} className="p-3 rounded-xl"
                    style={{ background: 'var(--nh-bg)', border: '1px solid var(--nh-border)' }}>
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <p className="text-sm font-semibold flex-1" style={{ color: 'var(--nh-text)' }}>
                        Q{pq.question_number}: {pq.question?.slice(0, 80)}{pq.question?.length > 80 ? '...' : ''}
                      </p>
                      <span className="text-sm font-bold flex-shrink-0 px-2 py-0.5 rounded-lg"
                        style={{
                          background: pq.score >= 70 ? 'rgba(139,184,168,0.15)' : pq.score >= 50 ? 'rgba(212,165,116,0.15)' : 'rgba(201,125,111,0.15)',
                          color: pq.score >= 70 ? '#5a9e8a' : pq.score >= 50 ? '#c4894a' : '#c97d6f',
                        }}>
                        {pq.score}/100
                      </span>
                    </div>
                    {pq.transcript && pq.transcript !== '(No transcript available)' && (
                      <p className="text-xs mb-2 italic" style={{ color: 'var(--nh-text-secondary)' }}>
                        "{pq.transcript.slice(0, 120)}{pq.transcript.length > 120 ? '...' : ''}"
                      </p>
                    )}
                    <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>{pq.feedback}</p>
                  </div>
                ))}
              </div>
            </GlassCard>
          )}

          <Button onClick={resetAll} className="gradient-bg text-white rounded-xl">
            <Mic className="w-4 h-4 mr-2" /> Start New Interview
          </Button>
        </motion.div>
      )}
    </div>
  );
}