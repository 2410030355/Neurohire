import React from 'react';
import { motion } from 'framer-motion';
import { Clock, Calendar, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { jsonFetch } from '@/api/http';
import { toast } from 'sonner';
import GlassCard from '@/components/shared/GlassCard';
import FitBadge from '@/components/shared/FitBadge';
import EmptyState from '@/components/shared/EmptyState';
import LoadingSkeleton from '@/components/shared/LoadingSkeleton';

export default function WaitlistPanel({ onSchedule }) {
  const queryClient = useQueryClient();
  const { data: rawEntries, isLoading } = useQuery({
    queryKey: ['waitlist'],
    queryFn: () => jsonFetch('/api/waitlist/'),
    initialData: [],
  });

  const entries = Array.isArray(rawEntries) ? rawEntries : (rawEntries?.results || []);

  const remove = async (entry) => {
    await jsonFetch(`/api/waitlist/${entry.id}/`, { method: 'DELETE' });
    queryClient.invalidateQueries({ queryKey: ['waitlist'] });
    toast.success('Removed from waitlist');
  };

  const moveToSchedule = (entry) => {
    onSchedule({ id: entry.candidate_id, name: entry.candidate_name, target_role: entry.role });
  };

  if (isLoading) return <LoadingSkeleton rows={3} type="list" />;
  if (!entries.length) return <EmptyState icon={Clock} title="Waitlist is Empty" description="Add candidates to the waitlist from Resume Analysis or Talent Search." />;

  return (
    <div className="space-y-3">
      {entries.map((entry, i) => (
        <motion.div key={entry.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
          <GlassCard hover={false} className="!p-4">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: '#F59E0B15' }}>
                  <Clock className="w-5 h-5" style={{ color: '#F59E0B' }} />
                </div>
                <div>
                  <h3 className="font-semibold" style={{ color: 'var(--nh-text)' }}>{entry.candidate_name}</h3>
                  <p className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>
                    {entry.role} {entry.match_score ? `• Score: ${entry.match_score}` : ''}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <FitBadge level={entry.priority === 'high' ? 'High' : entry.priority === 'low' ? 'Low' : 'Medium'} />
                <Button size="sm" onClick={() => moveToSchedule(entry)} className="gradient-bg text-white rounded-lg">
                  <Calendar className="w-3.5 h-3.5 mr-1" /> Schedule
                </Button>
                <Button size="sm" variant="ghost" onClick={() => remove(entry)} className="rounded-lg text-red-500 hover:text-red-700">
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          </GlassCard>
        </motion.div>
      ))}
    </div>
  );
}