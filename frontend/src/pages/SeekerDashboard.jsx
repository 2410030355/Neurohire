import React, { useState } from 'react';
import ProfileDropdown from '@/components/shared/ProfileDropdown';
import ThemeToggle from '@/components/ui/ThemeToggle';

import SeekerSidebar from '@/components/seeker/SeekerSidebar';
import ResumeImprover from '@/components/seeker/ResumeImprover';
import MockInterviewPanel from '@/components/seeker/MockInterviewPanel';
import JobBoard from '@/components/seeker/JobBoard';
import ProjectQA from '@/components/seeker/ProjectQA';

export default function SeekerDashboard() {
  const [activeTab, setActiveTab] = useState('resume');
  const [collapsed, setCollapsed] = useState(false);

  const tabTitles = {
    resume: { title: 'Resume Analyzer', desc: 'Get AI-powered feedback to improve your resume' },
    interview: { title: 'Mock Interview', desc: 'Practice with a tough AI interviewer' },
    jobs: { title: 'Job & Internship Board', desc: 'Discover opportunities and track your interviews' },
    project: { title: 'Project Q&A Generator', desc: 'Predict interview questions from your projects' },
  };

  const current = tabTitles[activeTab];

  return (
    <div className="flex min-h-screen" style={{ background: 'var(--nh-bg)' }}>
      <SeekerSidebar activeTab={activeTab} setActiveTab={setActiveTab} collapsed={collapsed} setCollapsed={setCollapsed} />

      <main className="flex-1 overflow-auto nh-scrollbar flex flex-col">
        {/* Top bar */}
        <div className="sticky top-0 z-10 flex items-center justify-end gap-3 px-6 py-3 bg-white/80 backdrop-blur border-b border-slate-100">
          <ThemeToggle />
          <ProfileDropdown role="seeker" />
        </div>

        <div className="flex-1 p-6 md:p-8">
          <div className="max-w-5xl mx-auto">
            <div className="mb-8">
              <h1 className="text-2xl md:text-3xl font-bold mb-1" style={{ color: 'var(--nh-text)' }}>{current.title}</h1>
              <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>{current.desc}</p>
            </div>

            {activeTab === 'resume' && <ResumeImprover />}
            {activeTab === 'interview' && <MockInterviewPanel />}
            {activeTab === 'jobs' && <JobBoard />}
            {activeTab === 'project' && <ProjectQA />}
          </div>
        </div>
      </main>
    </div>
  );
}