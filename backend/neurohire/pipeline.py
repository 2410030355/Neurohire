def save_user_profile(backend, user, response, *args, **kwargs):
    """
    Social auth pipeline step — ensures UserProfile exists after Google login.
    """
    try:
        from neurohire.models import UserProfile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'role': 'jobseeker'}
        )
        if created:
            # Try to get name from Google response
            full_name = response.get('name', '')
            if full_name:
                user.first_name = full_name.split(' ')[0]
                user.last_name = ' '.join(full_name.split(' ')[1:])
                user.save()
    except Exception as e:
        pass