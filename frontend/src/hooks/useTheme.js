/**
 * useTheme — shared theme hook used by both profile dropdowns
 */
import { useState, useEffect } from 'react';

export function useTheme() {
  const [light, setLight] = useState(() => localStorage.getItem('nh-theme') === 'light');

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

  return [light, () => setLight(v => !v)];
}