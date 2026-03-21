import React, { useState, useEffect } from 'react';
import { Moon, Sun } from 'lucide-react';
import { motion } from 'framer-motion';
export default function ThemeToggle() {
  const [light, setLight] = useState(() => {
    return localStorage.getItem('nh-theme') === 'light';
  });

  useEffect(() => {
    const root = document.documentElement;
    if (light) {
      root.setAttribute('data-theme', 'light');
      root.classList.remove('dark');
    } else {
      root.removeAttribute('data-theme');
      root.classList.add('dark');
    }
    localStorage.setItem('nh-theme', light ? 'light' : 'dark');
  }, [light]);

  return (
    <motion.button
      whileHover={{ scale: 1.08 }}
      whileTap={{ scale: 0.92 }}
      onClick={() => setLight(!light)}
      className="w-9 h-9 rounded-xl flex items-center justify-center transition-all"
      style={{
        background: 'var(--nh-primary-light)',
        border: '1px solid var(--nh-border)',
      }}
      aria-label="Toggle theme"
      title={light ? 'Switch to dark mode' : 'Switch to light mode'}
    >
      {light
        ? <Moon className="w-4 h-4" style={{ color: 'var(--nh-primary)' }} />
        : <Sun  className="w-4 h-4" style={{ color: 'var(--nh-primary)' }} />
      }
    </motion.button>
  );
}