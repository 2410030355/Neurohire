import { clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

export const isIframe = window.self !== window.top;

/**
 * createPageUrl - converts a page name to a route path.
 * Used across the app for navigation links.
 * e.g. createPageUrl('RecruiterDashboard') → '/RecruiterDashboard'
 */
export function createPageUrl(pageName) {
  if (!pageName) return '/';
  if (pageName === 'Home') return '/';
  return `/${pageName}`;
}