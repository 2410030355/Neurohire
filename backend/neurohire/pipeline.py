def save_user_profile(backend, user, response, request, *args, **kwargs):
    """
    Social auth pipeline — saves role from request and redirects accordingly.
    Role is passed as a query param: ?role=recruiter or ?role=jobseeker
    """
    try:
        from neurohire.models import UserProfile

        # Get role from request params
        role = request.GET.get('role', 'jobseeker')
        if role not in ('recruiter', 'jobseeker'):
            role = 'jobseeker'

        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'role': role}
        )
        if not created and profile.role != role:
            profile.role = role
            profile.save()

        # Set full name from Google
        full_name = response.get('name', '')
        if full_name and not user.first_name:
            user.first_name = full_name.split(' ')[0]
            user.last_name = ' '.join(full_name.split(' ')[1:])
            user.save()

        # Store role in session so redirect view can use it
        request.session['oauth_role'] = role

    except Exception as e:
        pass


def set_redirect_url(backend, user, response, request, *args, **kwargs):
    """
    Set redirect URL based on role after OAuth completes.
    """
    try:
        role = request.session.get('oauth_role', 'jobseeker')
        frontend = 'https://neurohire-bay.vercel.app'
        if role == 'recruiter':
            backend.strategy.session_set('next', f'{frontend}/RecruiterDashboard')
        else:
            backend.strategy.session_set('next', f'{frontend}/SeekerDashboard')
    except Exception:
        pass