def save_user_profile(backend, user, response, request, *args, **kwargs):
    """
    Social auth pipeline — saves role and name from Google OAuth.
    Role is passed as a query param: ?role=recruiter or ?role=jobseeker
    """
    try:
        from neurohire.models import UserProfile

        # ── Role requested on the login link (?role=recruiter|jobseeker) ──
        # social-auth keeps it in the session across the Google round-trip
        # (SOCIAL_AUTH_FIELDS_STORED_IN_SESSION = ['role']).
        from neurohire.access import is_allowed_recruiter_email
        requested = (
            backend.strategy.session_get('role')
            or request.GET.get('role')
            or ''
        ).strip().lower()

        email = (getattr(user, 'email', '') or response.get('email', '') or '').strip().lower()
        if requested == 'recruiter' and not (user.is_staff or is_allowed_recruiter_email(email)):
            requested = 'jobseeker'          # not on the allowlist -> seeker account
            request.session['oauth_recruiter_denied'] = True

        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'role': requested or 'jobseeker'}
        )
        # Only change an existing role when a role was explicitly requested.
        # (Previously a missing param silently demoted recruiters to seekers.)
        if not created and requested and profile.role != requested:
            profile.role = requested
            profile.save()
        role = profile.role

        # ── ALWAYS save name from Google — even if user already exists ──
        # Google returns: response['name'], response['given_name'], response['family_name']
        full_name = (
            response.get('name', '').strip() or
            f"{response.get('given_name', '')} {response.get('family_name', '')}".strip()
        )
        if full_name:
            parts = full_name.split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''
            user.save()
        elif not user.first_name and user.email:
            # Fallback: derive name from email prefix
            email_name = user.email.split('@')[0]
            clean = email_name.replace('.', ' ').replace('_', ' ').replace('-', ' ')
            parts = clean.split()
            user.first_name = parts[0].capitalize() if parts else email_name
            user.last_name = ' '.join(p.capitalize() for p in parts[1:]) if len(parts) > 1 else ''
            user.save()

        # ── Store role in session for redirect ─────────────────────
        request.session['oauth_role'] = role

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"save_user_profile error: {e}")


def set_redirect_url(backend, user, response, request, *args, **kwargs):
    """
    Set redirect URL based on role after OAuth completes.
    """
    try:
        role = request.session.get('oauth_role', 'jobseeker')
        frontend = 'https://neurohire-bay.vercel.app'
        if role == 'recruiter':
            backend.strategy.session_set('next', f'{frontend}/RecruiterDashboard')
        elif request.session.pop('oauth_recruiter_denied', False):
            # Asked for recruiter but the email is not on the allowlist
            backend.strategy.session_set('next', f'{frontend}/RecruiterAuth?error=not_approved')
        else:
            backend.strategy.session_set('next', f'{frontend}/SeekerDashboard')
    except Exception:
        pass