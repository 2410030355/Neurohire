import React from 'react';
import { motion } from 'framer-motion';
import { Brain, Briefcase, GraduationCap, ArrowRight, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';
import { createPageUrl } from '@/utils';
import ThemeToggle from '@/components/ui/ThemeToggle';

const roles = [
  {
    id: 'recruiter',
    icon: Briefcase,
    title: 'I\'m a Recruiter',
    desc: 'Upload resumes, analyze candidates with AI, search talent, and schedule interviews.',
    features: ['AI Resume Analysis', 'Talent Search', 'Interview Scheduling', 'Decision Analytics'],
    color: 'var(--nh-primary)',
    colorLight: 'var(--nh-primary-light)',
    page: 'RecruiterAuth',
  },
  {
    id: 'seeker',
    icon: GraduationCap,
    title: 'I\'m a Job Seeker',
    desc: 'Improve your resume, practice interviews with AI, and discover opportunities.',
    features: ['Resume Analyzer', 'Mock Interviews', 'Job Board', 'Project Q&A Generator'],
    color: 'var(--nh-secondary)',
    colorLight: 'var(--nh-primary-light)',
    page: 'SeekerAuth',
  },
];

export default function RoleSelect() {
  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--nh-bg)' }}>
      {/* Nav */}
      <nav className="px-6 py-4 flex items-center justify-between">
        <Link to={createPageUrl('Home')} className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold" style={{ color: 'var(--nh-text)' }}>NEUROHIRE</span>
        </Link>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <Link to={createPageUrl('Home')}>
            <Button variant="ghost" className="rounded-xl" style={{ color: 'var(--nh-text-secondary)' }}>
              <ArrowLeft className="w-4 h-4 mr-1" /> Back
            </Button>
          </Link>
        </div>
      </nav>

      {/* Content */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-3xl md:text-4xl font-bold mb-3" style={{ color: 'var(--nh-text)' }}>
            How would you like to use <span className="gradient-text">NeuroHire</span>?
          </h1>
          <p className="text-lg" style={{ color: 'var(--nh-text-secondary)' }}>
            Choose your role to get started with the right experience
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl w-full">
          {roles.map((role, i) => (
            <motion.div
              key={role.id}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + i * 0.15 }}
            >
              <Link to={createPageUrl(role.page)} className="block">
                <motion.div
                  whileHover={{ y: -6, boxShadow: 'var(--nh-shadow-lg)' }}
                  whileTap={{ scale: 0.98 }}
                  className="rounded-3xl p-8 h-full relative overflow-hidden group border"
                  style={{ background: 'var(--nh-card)', borderColor: 'var(--nh-border)', boxShadow: 'var(--nh-shadow-sm)' }}
                >
                  <div className="absolute top-0 right-0 w-32 h-32 rounded-full opacity-10 -translate-y-1/2 translate-x-1/2"
                    style={{ background: role.color }} />

                  <div className="relative z-10">
                    <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-6 transition-all"
                      style={{ background: role.colorLight }}>
                      <role.icon className="w-8 h-8" style={{ color: role.color }} />
                    </div>

                    <h2 className="text-2xl font-bold mb-3" style={{ color: 'var(--nh-text)' }}>{role.title}</h2>
                    <p className="mb-6 leading-relaxed" style={{ color: 'var(--nh-text-secondary)' }}>{role.desc}</p>

                    <div className="space-y-2 mb-8">
                      {role.features.map((f, j) => (
                        <div key={j} className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full" style={{ background: role.color }} />
                          <span className="text-sm font-medium" style={{ color: 'var(--nh-text)' }}>{f}</span>
                        </div>
                      ))}
                    </div>

                    <div className="flex items-center gap-2 font-semibold group-hover:gap-3 transition-all"
                      style={{ color: role.color }}>
                      Continue <ArrowRight className="w-5 h-5" />
                    </div>
                  </div>
                </motion.div>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}