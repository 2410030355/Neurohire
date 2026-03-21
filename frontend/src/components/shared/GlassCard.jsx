import React from 'react';
import { motion } from 'framer-motion';

/**
 * @param {Object} props
 * @param {React.ReactNode} props.children
 * @param {string} [props.className]
 * @param {boolean} [props.hover]
 * @param {number} [props.delay]
 * @param {() => void} [props.onClick]
 */
export default function GlassCard({ children, className = '', hover = true, delay = 0, onClick = undefined }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      whileHover={hover ? { y: -2, boxShadow: 'var(--nh-shadow-lg)' } : {}}
      onClick={onClick}
      className={`rounded-2xl p-6 border ${onClick ? 'cursor-pointer' : ''} ${className}`}
      style={{
        background: 'var(--nh-card)',
        borderColor: 'var(--nh-border)',
        boxShadow: 'var(--nh-shadow-sm)',
      }}
    >
      {children}
    </motion.div>
  );
}