import React from 'react';
import { motion } from 'framer-motion';
import { Inbox } from 'lucide-react';

/**
 * @param {Object} props
 * @param {React.ComponentType} [props.icon]
 * @param {string} props.title
 * @param {string} props.description
 * @param {React.ReactNode} [props.action]
 */
export default function EmptyState({ icon: Icon = Inbox, title, description, action = null }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center py-16 px-4"
    >
      <div className="w-16 h-16 rounded-2xl gradient-bg-subtle flex items-center justify-center mb-4">
        <Icon className="w-8 h-8" style={{ color: 'var(--nh-primary)' }} />
      </div>
      <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--nh-text)' }}>{title}</h3>
      <p className="text-sm text-center max-w-sm mb-4" style={{ color: 'var(--nh-text-secondary)' }}>{description}</p>
      {action}
    </motion.div>
  );
}