import React from 'react';
import { motion } from 'framer-motion';

export default function ScoreRing({
  score = 0,
  size = 64,
  strokeWidth = 5,
  label,
  color
}) {
  // 🛡️ clamp score safely
  const safeScore = Math.max(0, Math.min(100, Number(score) || 0));

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (safeScore / 100) * circumference;

  const getColor = () => {
    // ✅ explicit override (used by your CandidateCard)
    if (color) return color;

    // ✅ smart fallback coloring
    if (safeScore >= 75) return '#10B981'; // green
    if (safeScore >= 50) return '#F59E0B'; // orange
    return '#EF4444'; // red
  };

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          {/* background ring */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="var(--nh-border)"
            strokeWidth={strokeWidth}
          />

          {/* animated ring */}
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={getColor()}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 0.9, ease: 'easeOut' }}
          />
        </svg>

        {/* center number */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span
            className="text-sm font-bold"
            style={{ color: 'var(--nh-text)' }}
          >
            {safeScore}
          </span>
        </div>
      </div>

      {label && (
        <span
          className="text-xs font-medium"
          style={{ color: 'var(--nh-text-secondary)' }}
        >
          {label}
        </span>
      )}
    </div>
  );
}