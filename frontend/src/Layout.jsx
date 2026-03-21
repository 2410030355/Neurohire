import React, { useEffect } from 'react';

export default function Layout({ children, currentPageName }) {
  useEffect(() => {
    const theme = localStorage.getItem('nh-theme') || 'light';
    const root = document.documentElement;
    root.setAttribute('data-theme', theme);
    if (theme === 'dark') root.classList.add('dark');
    else root.classList.remove('dark');
  }, []);

  // Dashboard pages have their own layout with sidebars
  const fullWidthPages = ['RecruiterDashboard', 'SeekerDashboard', 'Home', 'RoleSelect'];
  const isFullWidth = fullWidthPages.includes(currentPageName);

  if (isFullWidth) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen" style={{ background: 'var(--nh-bg)' }}>
      {children}
    </div>
  );
}