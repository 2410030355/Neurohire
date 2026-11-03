"""
Who may act as a recruiter.

One rule, used everywhere a recruiter role is granted or checked:
  * email/password signup (RegisterView)
  * Google sign-in (pipeline.save_user_profile)
  * every recruiter-only API request (views.IsRecruiter)

Configure on Render with comma-separated env vars (see settings.py):
  RECRUITER_ALLOWED_EMAILS   exact addresses, e.g. you@gmail.com
  RECRUITER_ALLOWED_DOMAINS  whole domains, e.g. company.com
"""
from django.conf import settings


def _norm(values):
    return {v.strip().lower() for v in (values or []) if v and v.strip()}


def is_allowed_recruiter_email(email) -> bool:
    if not email or '@' not in email:
        return False
    email = email.strip().lower()
    if email in _norm(getattr(settings, 'ALLOWED_RECRUITER_EMAILS', [])):
        return True
    domain = email.rsplit('@', 1)[-1]
    return domain in _norm(getattr(settings, 'ALLOWED_RECRUITER_DOMAINS', []))


def user_email(user) -> str:
    return (getattr(user, 'email', '') or getattr(user, 'username', '') or '').strip().lower()


def recruiter_signup_hint() -> str:
    """Human-readable list of what is allowed, for error messages (no emails leaked)."""
    domains = sorted(_norm(getattr(settings, 'ALLOWED_RECRUITER_DOMAINS', [])))
    hint = ', '.join(domains) if domains else 'none'
    return f"Recruiter accounts are limited to approved emails or these domains: {hint}."
