import React from 'react';
import { motion } from 'framer-motion';
import { Calendar, Copy, CheckCircle, XCircle, Clock, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { jsonFetch } from '@/api/http';
import { format } from 'date-fns';
import { toast } from 'sonner';
import EmptyState from '@/components/shared/EmptyState';
import LoadingSkeleton from '@/components/shared/LoadingSkeleton';

const statusConfig = {
  scheduled: { bg: 'var(--nh-primary-light)', text: 'var(--nh-primary)', border: 'var(--nh-border)', label: 'Scheduled', icon: Clock },
  completed: { bg: '#ECFDF5', text: 'var(--nh-success)', border: '#A7F3D0', label: 'Completed', icon: CheckCircle },
  cancelled: { bg: '#FEF2F2', text: 'var(--nh-danger)', border: '#FECACA', label: 'Cancelled', icon: XCircle },
  no_show:   { bg: '#FFF7ED', text: 'var(--nh-warning)', border: '#FED7AA', label: 'No Show', icon: XCircle },
};

export default function ScheduledList() {
  const queryClient = useQueryClient();
  const { data: rawInterviews, isLoading } = useQuery({
    queryKey: ['interviews'],
    queryFn: () => jsonFetch('/api/interviews/'),
    initialData: [],
  });

  const interviews = Array.isArray(rawInterviews) ? rawInterviews : (rawInterviews?.results || []);

  const copyLink = (link) => {
    navigator.clipboard.writeText(link);
    toast.success('Interview link copied!');
  };

  const updateStatus = async (id, status) => {
    await jsonFetch(`/api/interviews/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
    queryClient.invalidateQueries({ queryKey: ['interviews'] });
    toast.success(`Interview marked as ${status}`);
  };

  if (isLoading) return <LoadingSkeleton rows={4} type="list" />;
  if (!interviews.length) return (
    <EmptyState icon={Calendar} title="No Interviews Scheduled" description="Schedule interviews from the Resume Analysis or Talent Search sections." />
  );

  return (
    <div className="grid grid-cols-1 gap-4 mt-2">
      {interviews.map((interview, i) => {
        const sc = statusConfig[interview.status] || statusConfig.scheduled;
        const StatusIcon = sc.icon;
        return (
          <motion.div
            key={interview.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
          >
            <div
              className="rounded-2xl p-5 shadow-md hover:shadow-lg transition-all border"
              style={{
                background: '#FFFFFF',
                borderColor: '#E2E8F0',
                boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
              }}
            >
              <div className="flex items-start justify-between flex-wrap gap-4">
                {/* Left */}
                <div className="flex items-center gap-4 min-w-0">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{ background: sc.bg }}
                  >
                    <User className="w-6 h-6" style={{ color: sc.text }} />
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-base truncate" style={{ color: '#0F172A' }}>
                      {interview.candidate_name}
                    </h3>
                    <p className="text-sm mt-0.5" style={{ color: '#475569' }}>
                      {interview.role || 'No role specified'}
                    </p>
                    {interview.scheduled_date && (
                      <p className="text-xs mt-1 flex items-center gap-1" style={{ color: '#64748B' }}>
                        <Calendar className="w-3 h-3" />
                        {format(new Date(interview.scheduled_date), 'EEEE, MMM d yyyy • h:mm a')}
                      </p>
                    )}
                    {interview.notes && (
                      <p className="text-xs mt-1 italic" style={{ color: '#64748B' }}>
                        "{interview.notes}"
                      </p>
                    )}
                  </div>
                </div>

                {/* Right */}
                <div className="flex items-center gap-2 flex-wrap">
                  {/* Status badge */}
                  <span
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border"
                    style={{ background: sc.bg, color: sc.text, borderColor: sc.border }}
                  >
                    <StatusIcon className="w-3 h-3" />
                    {sc.label}
                  </span>

                  {/* Copy link */}
                  {interview.interview_link && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => copyLink(interview.interview_link)}
                      className="rounded-xl text-xs"
                      style={{ borderColor: 'var(--nh-border)', color: 'var(--nh-text)' }}
                    >
                      <Copy className="w-3 h-3 mr-1" /> Copy Link
                    </Button>
                  )}

                  {/* Mark complete */}
                  {interview.status === 'scheduled' && (
                    <Button
                      size="sm"
                      onClick={() => updateStatus(interview.id, 'completed')}
                      className="rounded-xl text-xs"
                      style={{ background: '#ECFDF5', color: 'var(--nh-success)', border: '1px solid #A7F3D0' }}
                    >
                      <CheckCircle className="w-3 h-3 mr-1" /> Mark Done
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}