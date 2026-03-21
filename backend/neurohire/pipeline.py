"""
neurohire/pipeline.py
Custom social-auth pipeline step — runs after Google login
to ensure every user has a UserProfile with role='jobseeker'.
"""

def create_user_profile(backend, user, response, *args, **kwargs):
    """
    After Google OAuth creates the Django user,
    create a UserProfile with role='jobseeker' if one doesn't exist.
    """
    from neurohire.models import UserProfile
    UserProfile.objects.get_or_create(
        user=user,
        defaults={'role': 'jobseeker'}
    )