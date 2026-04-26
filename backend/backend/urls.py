from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter
from neurohire.views import clear_candidates
from neurohire.views import (
    CandidateViewSet,
    JobPostingViewSet,
    WaitlistEntryViewSet,
    AIDecisionLogViewSet,
    InterviewViewSet,
    MockInterviewViewSet,
    ResumeUploadView,
    SeekerResumeView,
    GitHubSearchView,
    ProjectQAView,
    MockInterviewStartView,
    MockInterviewAnalyzeView,
    TalentSearchView,
    RegisterView,
    LoginView,
    MeView,
    LogoutView,
    ProfileUpdateView,
    ChatbotView,
)
router = DefaultRouter()
router.register(r"candidates", CandidateViewSet, basename="candidates")
router.register(r"jobs", JobPostingViewSet)
router.register(r"waitlist", WaitlistEntryViewSet)
router.register(r"ai-decision-logs", AIDecisionLogViewSet)
router.register(r"interviews", InterviewViewSet)
router.register(r"mock-interviews", MockInterviewViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/upload-resume/", ResumeUploadView.as_view()),
    path("api/github-search/", GitHubSearchView.as_view()),
    path("api/project-qa/", ProjectQAView.as_view()),
    path("api/mock-interview/start/", MockInterviewStartView.as_view()),
    path("api/mock-interview/analyze/", MockInterviewAnalyzeView.as_view()),
    path("api/talent-search/", TalentSearchView.as_view()),
    path("api/auth/register/", csrf_exempt(RegisterView.as_view())),
    path("api/auth/login/", csrf_exempt(LoginView.as_view())),
    path("api/auth/me/", MeView.as_view()),
    path("api/auth/logout/", LogoutView.as_view()),
    path("api/candidates/clear/", clear_candidates),
    path("api/resume-improvement/", SeekerResumeView.as_view()),
    path("api/seeker-resume/", SeekerResumeView.as_view()),
    path("api/upload-file/", ResumeUploadView.as_view()),
    path("api/auth/profile/", ProfileUpdateView.as_view()),
    path("api/chatbot/", ChatbotView.as_view()),
    path("auth/", include("social_django.urls", namespace="social")),
]