import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Brain, Sparkles, Shield, Users, BarChart3, Zap, Sun, Moon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';
import { createPageUrl } from '@/utils';
import { useEffect } from 'react';

const features = [
  { icon: Brain,    title: 'AI-Powered Analysis',  desc: 'Deep resume parsing with NLP and evidence-backed skill validation' },
  { icon: Shield,   title: 'Bias-Free Hiring',      desc: 'Consistent, transparent scoring with full explainability' },
  { icon: BarChart3,title: 'Smart Metrics',         desc: 'Learning velocity, career trajectory, and role-skill matching' },
  { icon: Zap,      title: 'Instant Insights',      desc: 'Real-time candidate analysis with batch processing support' },
];

// Standalone toggle for pages without ProfileDropdown
function NavThemeToggle() {
  const [light, setLight] = useState(() => localStorage.getItem('nh-theme') === 'light');
  useEffect(() => {
    const root = document.documentElement;
    if (light) { root.setAttribute('data-theme', 'light'); root.classList.remove('dark'); }
    else        { root.removeAttribute('data-theme');       root.classList.add('dark'); }
    localStorage.setItem('nh-theme', light ? 'light' : 'dark');
  }, [light]);
  return (
    <motion.button whileHover={{ scale: 1.08 }} whileTap={{ scale: 0.92 }}
      onClick={() => setLight(v => !v)}
      className="w-9 h-9 rounded-xl flex items-center justify-center transition-all"
      style={{ background: 'var(--nh-primary-light)', border: '1px solid var(--nh-border)' }}
      aria-label="Toggle theme">
      {light
        ? <Moon className="w-4 h-4" style={{ color: 'var(--nh-primary)' }} />
        : <Sun  className="w-4 h-4" style={{ color: 'var(--nh-primary)' }} />}
    </motion.button>
  );
}

export default function Home() {
  const [hoveredFeature, setHoveredFeature] = useState(null);

  return (
    <div className="min-h-screen" style={{ background: 'var(--nh-bg)' }}>

      {/* ── Nav ── */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass-card border-b" style={{ borderColor: 'var(--nh-border)' }}>
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center shadow-md">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold gradient-text tracking-wide">NEUROHIRE</span>
          </div>
          <div className="flex items-center gap-3">
            <NavThemeToggle />
            <Link to={createPageUrl('RoleSelect')}>
              <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                <button
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all"
                  style={{
                    background: 'linear-gradient(135deg, #2DD4BF, #A78BFA)',
                    boxShadow: '0 4px 14px rgba(45,212,191,0.35)',
                  }}>
                  Get Started <ArrowRight className="w-4 h-4" />
                </button>
              </motion.div>
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="pt-32 pb-20 px-6 overflow-hidden">
        <div className="max-w-7xl mx-auto relative">

          {/* Glow blobs */}
          <div className="absolute -top-20 -right-20 w-96 h-96 rounded-full blur-3xl pointer-events-none"
            style={{ background: 'rgba(45,212,191,0.12)' }} />
          <div className="absolute -bottom-20 -left-20 w-72 h-72 rounded-full blur-3xl pointer-events-none"
            style={{ background: 'rgba(167,139,250,0.10)' }} />

          <motion.div initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }} className="text-center relative z-10">

            {/* Badge */}
            <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full mb-8"
              style={{ background: 'var(--nh-primary-light)', border: '1px solid rgba(45,212,191,0.25)' }}>
              <Sparkles className="w-4 h-4" style={{ color: 'var(--nh-primary)' }} />
              <span className="text-sm font-medium" style={{ color: 'var(--nh-primary)' }}>
                AI-Powered Recruitment Platform
              </span>
            </motion.div>

            {/* Headline */}
            <h1 className="text-5xl md:text-7xl font-extrabold leading-tight mb-6">
              <span style={{ color: 'var(--nh-text)' }}>Think Smart.</span>
              <br />
              <span className="gradient-text">Hire Right.</span>
            </h1>

            <p className="text-lg md:text-xl max-w-2xl mx-auto mb-10 leading-relaxed"
              style={{ color: 'var(--nh-text-secondary)' }}>
              NeuroHire uses advanced AI to analyze resumes, validate skills with evidence,
              and predict candidate success — giving recruiters superpowers and job seekers an edge.
            </p>

            {/* CTA buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link to={createPageUrl('RoleSelect')}>
                <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                  <button
                    className="flex items-center gap-2 px-8 py-4 rounded-xl text-lg font-semibold text-white transition-all"
                    style={{
                      background: 'linear-gradient(135deg, #2DD4BF, #A78BFA)',
                      boxShadow: '0 6px 24px rgba(45,212,191,0.35)',
                    }}>
                    Get Started Free <ArrowRight className="w-5 h-5" />
                  </button>
                </motion.div>
              </Link>

              <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                <button
                  className="flex items-center gap-2 px-8 py-4 rounded-xl text-lg font-semibold transition-all"
                  style={{
                    background: 'transparent',
                    border: '2px solid var(--nh-border)',
                    color: 'var(--nh-text)',
                  }}>
                  Watch Demo
                </button>
              </motion.div>
            </div>
          </motion.div>

          {/* Stats */}
          <motion.div initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.6 }}
            className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-20 max-w-4xl mx-auto">
            {[
              { num: '95%',  label: 'Accuracy Rate' },
              { num: '10x',  label: 'Faster Screening' },
              { num: '500+', label: 'Companies Trust Us' },
              { num: '50K+', label: 'Candidates Analyzed' },
            ].map((stat, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 + i * 0.1 }}
                className="text-center p-4 rounded-2xl"
                style={{ background: 'var(--nh-card)', border: '1px solid var(--nh-border)' }}>
                <div className="text-2xl md:text-3xl font-bold gradient-text">{stat.num}</div>
                <div className="text-sm mt-1" style={{ color: 'var(--nh-text-secondary)' }}>{stat.label}</div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}
            className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4" style={{ color: 'var(--nh-text)' }}>
              Powered by Intelligence
            </h2>
            <p className="text-lg max-w-xl mx-auto" style={{ color: 'var(--nh-text-secondary)' }}>
              Every feature is designed to make hiring smarter, faster, and more transparent.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((f, i) => (
              <motion.div key={i}
                initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }} transition={{ delay: i * 0.1 }}
                whileHover={{ y: -4 }}
                onMouseEnter={() => setHoveredFeature(i)}
                onMouseLeave={() => setHoveredFeature(null)}
                className="rounded-2xl p-6 transition-all cursor-default"
                style={{
                  background: 'var(--nh-card)',
                  border: `1px solid ${hoveredFeature === i ? 'rgba(45,212,191,0.4)' : 'var(--nh-border)'}`,
                  boxShadow: hoveredFeature === i ? '0 8px 24px rgba(45,212,191,0.12)' : 'none',
                }}>
                <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-4 transition-all"
                  style={{
                    background: hoveredFeature === i
                      ? 'linear-gradient(135deg, #2DD4BF, #A78BFA)'
                      : 'var(--nh-primary-light)',
                  }}>
                  <f.icon className="w-6 h-6"
                    style={{ color: hoveredFeature === i ? '#fff' : 'var(--nh-primary)' }} />
                </div>
                <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--nh-text)' }}>{f.title}</h3>
                <p className="text-sm leading-relaxed" style={{ color: 'var(--nh-text-secondary)' }}>{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Banner ── */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <motion.div initial={{ opacity: 0, scale: 0.95 }} whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="rounded-3xl p-12 md:p-16 text-center relative overflow-hidden"
            style={{ background: 'linear-gradient(135deg, #2DD4BF 0%, #A78BFA 100%)' }}>

            {/* Decorative circles */}
            <div className="absolute top-0 right-0 w-64 h-64 rounded-full -translate-y-1/2 translate-x-1/2"
              style={{ background: 'rgba(255,255,255,0.08)' }} />
            <div className="absolute bottom-0 left-0 w-48 h-48 rounded-full translate-y-1/2 -translate-x-1/2"
              style={{ background: 'rgba(255,255,255,0.08)' }} />

            <div className="relative z-10">
              <Users className="w-12 h-12 mx-auto mb-6" style={{ color: 'rgba(255,255,255,0.85)' }} />
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                Ready to Transform Your Hiring?
              </h2>
              <p className="text-lg max-w-xl mx-auto mb-8" style={{ color: 'rgba(255,255,255,0.8)' }}>
                Join hundreds of companies using NeuroHire to find the perfect candidates faster.
              </p>
              <Link to={createPageUrl('RoleSelect')}>
                <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }} className="inline-block">
                  <button
                    className="flex items-center gap-2 px-8 py-4 rounded-xl text-lg font-semibold transition-all"
                    style={{
                      background: '#0D1117',
                      color: '#2DD4BF',
                      boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
                    }}>
                    Start For Free <ArrowRight className="w-5 h-5" />
                  </button>
                </motion.div>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="py-8 px-6 border-t" style={{ borderColor: 'var(--nh-border)' }}>
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md gradient-bg flex items-center justify-center">
              <Brain className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold gradient-text">NEUROHIRE</span>
          </div>
          <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>
            © 2026 NeuroHire. Think Smart. Hire Right.
          </p>
        </div>
      </footer>
    </div>
  );
}