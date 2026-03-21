import React, { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { jsonFetch } from '@/api/http';

import Sidebar from '@/components/recruiter/Sidebar';
import ResumeUploader from '@/components/recruiter/ResumeUploader';
import CandidateCard from '@/components/recruiter/CandidateCard';
import TalentSearch from '@/components/recruiter/TalentSearch';
import ScheduledList from '@/components/recruiter/ScheduledList';
import WaitlistPanel from '@/components/recruiter/WaitlistPanel';
import AIAnalytics from '@/components/recruiter/AIAnalytics';
import ScheduleModal from '@/components/recruiter/ScheduleModal';
import EmptyState from '@/components/shared/EmptyState';
import LoadingSkeleton from '@/components/shared/LoadingSkeleton';
import ProfileDropdown from '@/components/shared/ProfileDropdown';

export default function RecruiterDashboard() {
  const [activeTab, setActiveTab] = useState('analysis');
  const [collapsed, setCollapsed] = useState(false);
  const [scheduleCandidate, setScheduleCandidate] = useState(null);
  const queryClient = useQueryClient();

  const { data: rawCandidates, isLoading: candidatesLoading } = useQuery({
    queryKey: ['candidates'],
    queryFn: () => jsonFetch('/api/candidates/'),
  });

  const candidates = Array.isArray(rawCandidates) ? rawCandidates : (rawCandidates?.results || []);

  const handleWaitlist = async (candidate) => {
    try {
      toast.success(`${candidate.name} added to waitlist`);
    } catch (err) {
      toast.error('Failed to add to waitlist');
    }
  };

  const refreshCandidates = () =>
    queryClient.invalidateQueries({ queryKey: ['candidates'] });

  const analyzedCandidates = candidates.filter(c => c.source === 'resume_upload');

  return (
    <div className="flex min-h-screen" style={{ background: 'var(--nh-bg)' }}>
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        collapsed={collapsed}
        setCollapsed={setCollapsed}
      />

      <main className="flex-1 overflow-auto nh-scrollbar flex flex-col">
        {/* Top bar — ThemeToggle is inside ProfileDropdown, no separate toggle needed */}
        <div
          className="sticky top-0 z-10 flex items-center justify-end gap-3 px-6 py-3 backdrop-blur border-b"
          style={{ background: 'var(--nh-glass)', borderColor: 'var(--nh-border)' }}
        >
          <ProfileDropdown role="recruiter" />
        </div>

        <div className="flex-1 p-6 md:p-8">
          <div className="max-w-6xl mx-auto">

            {activeTab === 'analysis' && (
              <>
                <div className="mb-8">
                  <h1 className="text-2xl md:text-3xl font-bold mb-1" style={{ color: 'var(--nh-text)' }}>
                    Resume Analysis
                  </h1>
                  <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>
                    Upload and analyze candidate resumes with AI
                  </p>
                </div>

                <ResumeUploader onAnalysisComplete={refreshCandidates} />

                {candidatesLoading ? (
                  <LoadingSkeleton rows={3} />
                ) : analyzedCandidates.length > 0 ? (
                  <>
                    <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--nh-text)' }}>
                      Analyzed Candidates ({analyzedCandidates.length})
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                      {analyzedCandidates.map((c, i) => (
                        <CandidateCard
                          key={c.mongo_id || c.id || i}
                          candidate={c}
                          index={i}
                          onSchedule={setScheduleCandidate}
                          onWaitlist={handleWaitlist}
                        />
                      ))}
                    </div>
                  </>
                ) : (
                  <EmptyState title="No analyzed candidates yet" />
                )}
              </>
            )}

            {activeTab === 'talent' && (
              <>
                <div className="mb-8">
                  <h1 className="text-2xl md:text-3xl font-bold mb-1" style={{ color: 'var(--nh-text)' }}>
                    Talent Search
                  </h1>
                  <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>
                    Find candidates across external platforms
                  </p>
                </div>
                <TalentSearch onSchedule={setScheduleCandidate} onWaitlist={handleWaitlist} />
              </>
            )}

            {activeTab === 'scheduled' && (
              <>
                <div className="mb-8">
                  <h1 className="text-2xl md:text-3xl font-bold mb-1" style={{ color: 'var(--nh-text)' }}>
                    Scheduled Interviews
                  </h1>
                  <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>
                    Manage upcoming interviews
                  </p>
                </div>
                <ScheduledList />
              </>
            )}

            {activeTab === 'waitlist' && (
              <>
                <div className="mb-8">
                  <h1 className="text-2xl md:text-3xl font-bold mb-1" style={{ color: 'var(--nh-text)' }}>
                    Waitlist
                  </h1>
                  <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>
                    Candidates waiting for review
                  </p>
                </div>
                <WaitlistPanel onSchedule={setScheduleCandidate} />
              </>
            )}

            {activeTab === 'analytics' && (
              <>
                <div className="mb-8">
                  <h1 className="text-2xl md:text-3xl font-bold mb-1" style={{ color: 'var(--nh-text)' }}>
                    AI Decision Analytics
                  </h1>
                  <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>
                    Human-AI disagreement tracking and insights
                  </p>
                </div>
                <AIAnalytics />
              </>
            )}

          </div>
        </div>
      </main>

      <AnimatePresence>
        {scheduleCandidate && (
          <ScheduleModal
            candidate={scheduleCandidate}
            onClose={() => setScheduleCandidate(null)}
            onScheduled={() => {
              queryClient.invalidateQueries({ queryKey: ['interviews'] });
              queryClient.invalidateQueries({ queryKey: ['candidates'] });
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}