import React from 'react';

export default function FitBadge({ level }) {
  const config = {
    High:   { bg: 'var(--nh-success)', bgLight: '#ECFDF5', text: '#065F46' },
    Medium: { bg: 'var(--nh-warning)', bgLight: '#FFF7ED', text: '#B45309' },
    Low:   { bg: 'var(--nh-danger)', bgLight: '#FEF2F2', text: '#B91C1C' },
  };
  const c = config[level] || config.Medium;

  return (
    <span
      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border"
      style={{
        background: c.bgLight,
        color: c.text,
        borderColor: 'var(--nh-border-light)',
      }}
    >
      {level}
    </span>
  );
}