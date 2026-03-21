import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { X, Copy, Calendar, Clock, CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { jsonFetch } from '@/api/http';
import { toast } from 'sonner';

export default function ScheduleModal({ candidate, onClose, onScheduled }) {
  const [date, setDate] = useState('');
  const [time, setTime] = useState('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);

  const generateLink = () => {
    return `https://neurohire.app/interview/${Math.random().toString(36).substring(2, 10)}`;
  };

  const handleSchedule = async () => {
    if (!date || !time) return toast.error('Please select date and time');
    setSaving(true);

    const link = generateLink();
    await jsonFetch('/api/interviews/', {
      method: 'POST',
      body: JSON.stringify({
        candidate_id: candidate.id,
        candidate_name: candidate.name,
        role: candidate.target_role,
        scheduled_date: `${date}T${time}:00`,
        interview_link: link,
        status: 'scheduled',
        notes,
      }),
    });

    if (candidate.id) {
      await jsonFetch(`/api/candidates/${candidate.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ status: 'scheduled' }),
      });
    }

    setSaving(false);
    toast.success('Interview scheduled!');
    onScheduled?.();
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)' }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0, y: 10 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.95, opacity: 0, y: 10 }}
        transition={{ duration: 0.2 }}
        className="w-full max-w-md rounded-2xl p-8 shadow-2xl border border-slate-200"
        style={{ background: 'var(--nh-card)' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center">
              <Calendar className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Schedule Interview</h2>
              <p className="text-xs text-slate-500">Set date, time and notes</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-xl transition-colors">
            <X className="w-4 h-4 text-slate-500" />
          </button>
        </div>

        <div className="p-4 rounded-xl mb-5 bg-indigo-50 border border-indigo-100">
          <p className="text-sm font-semibold text-slate-800">{candidate.name}</p>
          <p className="text-xs text-indigo-600 mt-0.5">{candidate.target_role || 'No role specified'}</p>
        </div>

        <div className="space-y-4">
          <div>
            <Label className="text-sm font-medium mb-1.5 block text-slate-700">Date</Label>
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)}
              className="rounded-xl border-slate-200 bg-white text-slate-900 focus:border-indigo-400 focus:ring-indigo-400" />
          </div>
          <div>
            <Label className="text-sm font-medium mb-1.5 block text-slate-700">Time</Label>
            <Input type="time" value={time} onChange={(e) => setTime(e.target.value)}
              className="rounded-xl border-slate-200 bg-white text-slate-900 focus:border-indigo-400 focus:ring-indigo-400" />
          </div>
          <div>
            <Label className="text-sm font-medium mb-1.5 block text-slate-700">Notes (optional)</Label>
            <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Add interview notes..."
              className="rounded-xl border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 focus:border-indigo-400" />
          </div>
        </div>

        <div className="flex gap-3 mt-7 justify-end">
          <Button variant="outline" onClick={onClose} className="rounded-xl border-slate-200 text-slate-700 hover:bg-slate-50 px-5">
            Cancel
          </Button>
          <Button onClick={handleSchedule} disabled={saving} className="rounded-xl px-5 bg-indigo-600 hover:bg-indigo-700 text-white">
            {saving ? <Clock className="w-4 h-4 animate-spin mr-1.5" /> : <Calendar className="w-4 h-4 mr-1.5" />}
            Schedule Interview
          </Button>
        </div>
      </motion.div>
    </div>
  );
}