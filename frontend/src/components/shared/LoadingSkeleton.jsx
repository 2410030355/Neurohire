import React from 'react';

export default function LoadingSkeleton({ rows = 3, type = 'card' }) {
  if (type === 'card') {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {Array(rows).fill(0).map((_, i) => (
          <div key={i} className="glass-card rounded-2xl p-6 animate-pulse">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-full" style={{ background: 'var(--nh-border)' }} />
              <div className="flex-1">
                <div className="h-4 rounded w-3/4 mb-2" style={{ background: 'var(--nh-border)' }} />
                <div className="h-3 rounded w-1/2" style={{ background: 'var(--nh-border)' }} />
              </div>
            </div>
            <div className="space-y-3">
              <div className="h-3 rounded w-full" style={{ background: 'var(--nh-border)' }} />
              <div className="h-3 rounded w-5/6" style={{ background: 'var(--nh-border)' }} />
              <div className="flex gap-2 mt-4">
                <div className="h-8 rounded-lg w-20" style={{ background: 'var(--nh-border)' }} />
                <div className="h-8 rounded-lg w-20" style={{ background: 'var(--nh-border)' }} />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {Array(rows).fill(0).map((_, i) => (
        <div key={i} className="glass-card rounded-xl p-4 animate-pulse flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg" style={{ background: 'var(--nh-border)' }} />
          <div className="flex-1">
            <div className="h-4 rounded w-1/3 mb-2" style={{ background: 'var(--nh-border)' }} />
            <div className="h-3 rounded w-2/3" style={{ background: 'var(--nh-border)' }} />
          </div>
          <div className="h-6 rounded-full w-16" style={{ background: 'var(--nh-border)' }} />
        </div>
      ))}
    </div>
  );
}