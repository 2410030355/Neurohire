import React from 'react';
import { motion } from 'framer-motion';
import { Brain, FileText, Mic, Briefcase, MessageSquare, LogOut, ChevronLeft, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { createPageUrl } from '@/utils';

const menuItems = [
  { icon: FileText,      label: 'Resume Analyzer', id: 'resume'    },
  { icon: Mic,           label: 'Mock Interview',  id: 'interview' },
  { icon: Briefcase,     label: 'Job Board',       id: 'jobs'      },
  { icon: MessageSquare, label: 'Project Q&A',     id: 'project'   },
];

export default function SeekerSidebar({ activeTab, setActiveTab, collapsed, setCollapsed }) {
  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 72 : 260 }}
      className="h-screen sticky top-0 flex flex-col border-r z-40"
      style={{
        background: 'var(--nh-bg-secondary)',
        borderColor: 'var(--nh-border)',
      }}
    >
      {/* ── Logo ── */}
      <div className="p-4 flex items-center justify-between border-b" style={{ borderColor: 'var(--nh-border)' }}>
        {!collapsed ? (
          <Link to={createPageUrl('Home')} className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center flex-shrink-0 shadow-md">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="text-base font-bold gradient-text tracking-wide">NEUROHIRE</span>
          </Link>
        ) : (
          <div className="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center mx-auto shadow-md">
            <Brain className="w-5 h-5 text-white" />
          </div>
        )}
      </div>

      {/* ── Collapse toggle ── */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-16 w-6 h-6 rounded-full flex items-center justify-center z-50 shadow-md"
        style={{ background: 'var(--nh-card)', border: '1px solid var(--nh-border)' }}
      >
        {collapsed
          ? <ChevronRight className="w-3 h-3" style={{ color: 'var(--nh-text-secondary)' }} />
          : <ChevronLeft  className="w-3 h-3" style={{ color: 'var(--nh-text-secondary)' }} />
        }
      </button>

      {/* ── Nav ── */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto nh-scrollbar">
        {menuItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all text-left relative overflow-hidden"
              style={{ background: isActive ? 'var(--nh-primary-light)' : 'transparent' }}
            >
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 rounded-r-full"
                  style={{ background: 'var(--nh-primary)' }} />
              )}
              <item.icon
                className="w-5 h-5 flex-shrink-0"
                style={{ color: isActive ? 'var(--nh-primary)' : 'var(--nh-text-secondary)' }}
              />
              {!collapsed && (
                <span className="text-sm font-medium truncate"
                  style={{ color: isActive ? 'var(--nh-primary)' : 'var(--nh-text-secondary)' }}>
                  {item.label}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* ── Bottom: Exit only ── */}
      <div className="p-3 border-t" style={{ borderColor: 'var(--nh-border)' }}>
        <Link to={createPageUrl('Home')}>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all hover:opacity-80">
            <LogOut className="w-5 h-5 flex-shrink-0" style={{ color: 'var(--nh-text-secondary)' }} />
            {!collapsed && (
              <span className="text-sm" style={{ color: 'var(--nh-text-secondary)' }}>Exit</span>
            )}
          </button>
        </Link>
      </div>
    </motion.aside>
  );
}