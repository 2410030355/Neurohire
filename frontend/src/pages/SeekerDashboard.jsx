import React, { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import SeekerSidebar from '@/components/seeker/SeekerSidebar';
import ResumeImprover from '@/components/seeker/ResumeImprover';
import MockInterviewPanel from '@/components/seeker/MockInterviewPanel';
import JobBoard from '@/components/seeker/JobBoard';
import ProjectQA from '@/components/seeker/ProjectQA';
import ProfileDropdown from '@/components/shared/ProfileDropdown';

export default function SeekerDashboard() {
  const [activeTab, setActiveTab] = useState('resume');
  const [collapsed, setCollapsed]   = useState(false);

  return (
    <div className="flex min-h-screen" style={{ background: 'var(--nh-bg)' }}>
      <SeekerSidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        collapsed={collapsed}
        setCollapsed={setCollapsed}
      />

      <main className="flex-1 overflow-auto nh-scrollbar flex flex-col">
        {/* ── Top bar — ThemeToggle lives inside ProfileDropdown only ── */}
        <div
          className="sticky top-0 z-10 flex items-center justify-end gap-3 px-6 py-3 backdrop-blur border-b"
          style={{ background: 'var(--nh-glass)', borderColor: 'var(--nh-border)' }}
        >
          <ProfileDropdown role="jobseeker" />
        </div>

        <div className="flex-1 p-6 md:p-8">
          <div className="max-w-5xl mx-auto">

            {activeTab === 'resume' && (
              <>
                <div className="mb-8">
                  <h1 className="text-2xl md:text-3xl font-bold mb-1" style={{ color: 'var(--nh-text)' }}>
                    Resume Analyzer
                  </h1>
                  <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>
                    Get AI-powered feedback to improve your resume
                  </p>
                </div>
                <ResumeImprover />
              </>
            )}

            {activeTab === 'interview' && (
              <>
                <div className="mb-8">
                  <h1 className="text-2xl md:text-3xl font-bold mb-1" style={{ color: 'var(--nh-text)' }}>
                    Mock Interview
                  </h1>
                  <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>
                    Practice with AI-generated role-specific questions
                  </p>
                </div>
                <MockInterviewPanel />
              </>
            )}

            {activeTab === 'jobs' && (
              <>
                <div className="mb-8">
                  <h1 className="text-2xl md:text-3xl font-bold mb-1" style={{ color: 'var(--nh-text)' }}>
                    Job Board
                  </h1>
                  <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>
                    Browse active job opportunities
                  </p>
                </div>
                <JobBoard />
              </>
            )}

            {activeTab === 'project' && (
              <>
                <div className="mb-8">
                  <h1 className="text-2xl md:text-3xl font-bold mb-1" style={{ color: 'var(--nh-text)' }}>
                    Project Q&A Trainer
                  </h1>
                  <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>
                    Generate interview questions from your project descriptions
                  </p>
                </div>
                <ProjectQA />
              </>
            )}

          </div>
        </div>
      </main>
    </div>
  );
}