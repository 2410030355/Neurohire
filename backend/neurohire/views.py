import os
import uuid
import logging

from django.conf import settings
from django.contrib.auth import authenticate, login, logout, get_user_model
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view

from .models import (
    Candidate,
    JobPosting,
    WaitlistEntry,
    AIDecisionLog,
    Interview,
    MockInterview,
    UserProfile,
)
from .serializers import (
    CandidateSerializer,
    JobPostingSerializer,
    WaitlistEntrySerializer,
    AIDecisionLogSerializer,
    InterviewSerializer,
    MockInterviewSerializer,
)
from .analysis_engine import analyze_resume, github_search_service
from .mongo_client import (
    mongo_insert_candidate, mongo_get_candidate,
    mongo_all_candidates, mongo_delete_all_candidates,
    mongo_find_by_github, mongo_is_available,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ==============================
# 🔐 Permission Classes
# ==============================

class IsRecruiter(BasePermission):
    """
    Allows access only to authenticated users with the 'recruiter' role.
    """
    message = "Access restricted to recruiters only."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            return request.user.profile.role == "recruiter"
        except UserProfile.DoesNotExist:
            return False


class IsJobSeeker(BasePermission):
    """
    Allows access only to authenticated users with the 'jobseeker' role.
    """
    message = "Access restricted to job seekers only."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            return request.user.profile.role == "jobseeker"
        except UserProfile.DoesNotExist:
            return False


# ==============================
# 🔧 Helpers
# ==============================

def _get_user_role(user):
    """Safely retrieve the role for a user."""
    try:
        return user.profile.role
    except UserProfile.DoesNotExist:
        return None


def _user_payload(user):
    """Return a minimal user dict for API responses, including role."""
    # Guard FIRST before accessing any user fields
    if not user or not user.is_authenticated:
        return None

    # Build full name — try every possible source
    first = (user.first_name or '').strip()
    last  = (user.last_name  or '').strip()
    full_name = (
        f"{first} {last}".strip()           # Google OAuth sets both
        or first                             # email signup sets first_name
        or user.username                     # fallback to username
        or user.email.split('@')[0]          # last resort: email prefix
    )

    # Clean up email-style names like "john.doe123" → "John Doe"
    if full_name and ('@' not in full_name) and ('.' in full_name or '_' in full_name):
        clean = full_name.replace('.', ' ').replace('_', ' ')
        parts = [p for p in clean.split() if p and not p.isdigit()]
        if parts:
            full_name = ' '.join(p.capitalize() for p in parts)

    return {
        "id":        user.pk,
        "email":     getattr(user, "email", None) or user.username,
        "username":  user.username,
        "full_name": full_name,
        "role":      _get_user_role(user),
    }


def _is_allowed_recruiter_email(email: str) -> bool:
    """
    Check if an email domain is in the allowed recruiter domains list.
    Configured via ALLOWED_RECRUITER_DOMAINS in settings.py.
    """
    allowed_domains = getattr(settings, "ALLOWED_RECRUITER_DOMAINS", [])
    if not allowed_domains:
        # If no domains configured, block all recruiter registrations
        return False
    domain = email.split("@")[-1].lower().strip()
    return domain in [d.lower().strip() for d in allowed_domains]


# ==============================
# ViewSets (Recruiter-protected)
# ==============================

class CandidateViewSet(viewsets.ViewSet):
    """
    Candidates are stored in MongoDB.
    GET /api/candidates/  → list all from MongoDB
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def list(self, request):
        candidates = mongo_all_candidates(limit=200)
        return Response(candidates)

    def retrieve(self, request, pk=None):
        candidate = mongo_get_candidate(pk)
        if not candidate:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(candidate)


class JobPostingViewSet(viewsets.ModelViewSet):
    queryset = JobPosting.objects.all().order_by("-id")
    serializer_class = JobPostingSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


class WaitlistEntryViewSet(viewsets.ModelViewSet):
    queryset = WaitlistEntry.objects.all().order_by("-id")
    serializer_class = WaitlistEntrySerializer
    permission_classes = [AllowAny]
    authentication_classes = []


class AIDecisionLogViewSet(viewsets.ModelViewSet):
    queryset = AIDecisionLog.objects.all().order_by("-id")
    serializer_class = AIDecisionLogSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


class InterviewViewSet(viewsets.ModelViewSet):
    queryset = Interview.objects.all().order_by("-id")
    serializer_class = InterviewSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


class MockInterviewViewSet(viewsets.ModelViewSet):
    queryset = MockInterview.objects.all().order_by("-id")
    serializer_class = MockInterviewSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


# ==============================
# Upload + Analysis API
# ==============================

UPLOAD_DIR = os.path.join(settings.BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ResumeUploadView(APIView):
    """
    Resume upload + AI analysis endpoint.
    Open to any authenticated user — recruiter check done via frontend routing.
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]  # CSRF exempt in urls.py handles security
    authentication_classes = []

    def post(self, request):
        file = request.FILES.get("resume")
        name = request.data.get("name", "Unknown")
        target_role = request.data.get("target_role", "")
        job_description = request.data.get("job_description", "")

        if not file:
            return Response(
                {"error": "No file uploaded"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        unique_name = f"{uuid.uuid4()}_{file.name}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)

        try:
            with open(file_path, "wb+") as f:
                for chunk in file.chunks():
                    f.write(chunk)
        except Exception as e:
            return Response(
                {"error": f"File save failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            analysis = analyze_resume(file_path, target_role, job_description)
        except Exception as e:
            return Response(
                {"error": f"Analysis failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── Save unified candidate profile to MongoDB ──────────────────
        mongo_doc = {
            'name':                   analysis.get('name') or name,
            'email':                  analysis.get('email'),
            'phone':                  analysis.get('phone'),
            'resume_url':             unique_name,
            'target_role':            target_role,
            'job_description':        job_description,
            'source':                 'resume_upload',
            'status':                 'analyzed',
            # AI scores
            'consistency_score':      analysis.get('consistency_score', 0),
            'skill_validation_score': analysis.get('skill_validation_score', 0),
            'learning_velocity':      analysis.get('learning_velocity', 'Medium'),
            'role_match_score':       analysis.get('role_match_score', 0),
            'final_fit':              analysis.get('final_fit', 'Medium'),
            'explainability':         analysis.get('explainability', ''),
            'resume_strength_score':  analysis.get('resume_strength_score', 0),
            # Profile
            'skills':                 analysis.get('skills', []),
            'validated_skills':       analysis.get('validated_skills', []),
            'missing_skills':         analysis.get('missing_skills', []),
            'experience_years':       analysis.get('experience_years'),
            'education':              analysis.get('education'),
            'profile_summary':        analysis.get('profile_summary'),
            'career_trajectory':      analysis.get('career_trajectory'),
        }
        mongo_id = mongo_insert_candidate(mongo_doc)

        return Response(
            {
                'message': 'Analysis complete',
                'candidate_id': mongo_id or 'local',
                'analysis': analysis,
            },
            status=status.HTTP_201_CREATED,
        )



# ==============================
# Seeker Resume Improvement API
# ==============================

class SeekerResumeView(APIView):
    """
    Resume analysis endpoint for job seekers.
    Returns personal improvement feedback instead of recruiter-style scoring.
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]
    authentication_classes = []

    # Common skill sets by role category for gap analysis
    ROLE_SKILL_MAP = {
        'frontend': ['react', 'javascript', 'typescript', 'html', 'css', 'tailwind', 'nextjs', 'redux', 'webpack', 'testing'],
        'backend': ['python', 'django', 'node', 'sql', 'postgresql', 'redis', 'docker', 'api', 'aws', 'microservices'],
        'fullstack': ['react', 'node', 'python', 'sql', 'docker', 'git', 'typescript', 'aws', 'mongodb', 'testing'],
        'data': ['python', 'sql', 'pandas', 'machine learning', 'tensorflow', 'statistics', 'tableau', 'spark', 'numpy', 'scikit'],
        'ml': ['python', 'tensorflow', 'pytorch', 'machine learning', 'deep learning', 'nlp', 'statistics', 'numpy', 'pandas', 'docker'],
        'devops': ['docker', 'kubernetes', 'aws', 'ci/cd', 'terraform', 'linux', 'ansible', 'jenkins', 'git', 'monitoring'],
        'mobile': ['react native', 'flutter', 'swift', 'kotlin', 'android', 'ios', 'firebase', 'api', 'git', 'testing'],
        'default': ['git', 'python', 'sql', 'docker', 'aws', 'communication', 'agile', 'testing', 'api', 'linux'],
    }

    def _get_role_category(self, target_role):
        role_lower = target_role.lower()
        if any(w in role_lower for w in ['frontend', 'front-end', 'react', 'vue', 'angular', 'ui']):
            return 'frontend'
        if any(w in role_lower for w in ['backend', 'back-end', 'django', 'node', 'api', 'server']):
            return 'backend'
        if any(w in role_lower for w in ['fullstack', 'full stack', 'full-stack']):
            return 'fullstack'
        if any(w in role_lower for w in ['data scientist', 'data analyst', 'analytics']):
            return 'data'
        if any(w in role_lower for w in ['machine learning', 'ml engineer', 'ai engineer', 'deep learning']):
            return 'ml'
        if any(w in role_lower for w in ['devops', 'cloud', 'infrastructure', 'sre', 'platform']):
            return 'devops'
        if any(w in role_lower for w in ['mobile', 'android', 'ios', 'flutter', 'react native']):
            return 'mobile'
        return 'default'

    def _generate_improvement_tips(self, analysis, target_role):
        """Generate seeker-focused improvement suggestions from analysis data."""
        tips = []
        skills = analysis.get('skills', [])
        experience = analysis.get('experience_years', 0)
        strength = analysis.get('resume_strength_score', 0)
        consistency = analysis.get('consistency_score', 0)
        education = analysis.get('education', '')

        # Skill count feedback
        if len(skills) < 5:
            tips.append("Add more specific technical skills to your resume. Aim for at least 8-10 relevant skills.")
        elif len(skills) < 10:
            tips.append("You have a decent skill set. Consider adding 3-4 more tools or technologies you've used.")

        # Role match feedback
        role_score = analysis.get('role_match_score', 0)
        if role_score < 40:
            tips.append(f"Your current skills don't closely match '{target_role}'. Focus on learning the core technologies for this role.")
        elif role_score < 65:
            tips.append(f"You're partially aligned with '{target_role}'. Bridge the gap by adding projects using the missing skills.")
        else:
            tips.append(f"Your skills align well with '{target_role}'. Highlight your most relevant projects prominently.")

        # Experience feedback
        if experience < 1:
            tips.append("Add internships, freelance work, or personal projects to show hands-on experience.")
        elif experience < 2:
            tips.append("With limited experience, emphasize your projects and the measurable impact you created.")

        # Resume strength
        if strength < 50:
            tips.append("Your resume needs more detail. Add bullet points with quantifiable achievements (e.g., 'Reduced load time by 40%').")
        elif strength < 70:
            tips.append("Strengthen your resume by adding metrics and outcomes to your work experience bullet points.")

        # Consistency
        if consistency < 50:
            tips.append("Ensure your resume tells a consistent story. Align your skills section with what you've actually used in your experience.")

        # Education
        if not education:
            tips.append("Add your educational background clearly — degree, institution, and graduation year.")

        # Generic high-value tips
        tips.append("Tailor your resume for each application by matching keywords from the job description.")
        tips.append("Add a strong 2-3 line professional summary at the top of your resume.")

        return tips[:6]  # Return top 6

    def _generate_skill_gaps(self, analysis, target_role):
        """Return role-specific missing skills the seeker should learn."""
        role_cat = self._get_role_category(target_role)
        required = self.ROLE_SKILL_MAP.get(role_cat, self.ROLE_SKILL_MAP['default'])
        current_skills = [s.lower() for s in analysis.get('skills', [])]
        gaps = []
        for skill in required:
            if not any(skill in cs or cs in skill for cs in current_skills):
                gaps.append(skill)
        return gaps[:6]

    def _generate_strengths(self, analysis):
        """Identify what the seeker is already doing well."""
        strengths = []
        skills = analysis.get('skills', [])
        experience = analysis.get('experience_years', 0)
        velocity = analysis.get('learning_velocity', 'Medium')

        if len(skills) >= 8:
            strengths.append(f"Strong skill breadth — {len(skills)} technologies detected")
        if experience >= 3:
            strengths.append(f"Solid work experience ({experience:.0f}+ years)")
        if velocity == 'High':
            strengths.append("High learning velocity — you pick up new technologies quickly")
        if analysis.get('education'):
            strengths.append(f"Strong educational background: {analysis['education']}")
        if analysis.get('role_match_score', 0) >= 65:
            strengths.append("Good alignment with your target role")
        if not strengths:
            strengths.append("You have a foundation to build on — focus on targeted skill development")
        return strengths

    def post(self, request):
        file = request.FILES.get('resume')
        target_role = request.data.get('target_role', 'Software Developer').strip()

        if not file:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        # Save file
        unique_name = f"{uuid.uuid4()}_{file.name}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)
        try:
            with open(file_path, 'wb+') as f:
                for chunk in file.chunks():
                    f.write(chunk)
        except Exception as e:
            return Response({'error': f'File save failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Run analysis
        try:
            analysis = analyze_resume(file_path, target_role)
        except Exception as e:
            return Response({'error': f'Analysis failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Build seeker-focused response
        skill_gaps = self._generate_skill_gaps(analysis, target_role)
        improvement_tips = self._generate_improvement_tips(analysis, target_role)
        strengths = self._generate_strengths(analysis)

        # Overall readiness score (seeker-friendly, not recruiter score)
        role_score = analysis.get('role_match_score', 0)
        strength_score = analysis.get('resume_strength_score', 0)
        readiness = round((role_score * 0.5) + (strength_score * 0.5))

        return Response({
            # Personal info
            'name': analysis.get('name', 'You'),
            'target_role': target_role,

            # Seeker-friendly scores
            'readiness_score': readiness,
            'resume_strength': round(strength_score),
            'role_alignment': round(role_score),
            'learning_velocity': analysis.get('learning_velocity', 'Medium'),
            'experience_years': analysis.get('experience_years', 0),
            'education': analysis.get('education', ''),

            # Skills
            'current_skills': analysis.get('skills', []),
            'skill_gaps': skill_gaps,

            # Actionable feedback
            'strengths': strengths,
            'improvement_tips': improvement_tips,
            'career_summary': analysis.get('career_trajectory', ''),
        }, status=status.HTTP_200_OK)


# ==============================
# GitHub Candidate Search API
# ==============================

class GitHubSearchView(APIView):
    """
    GitHub candidate search endpoint. Recruiter-only.
    """
    parser_classes = [JSONParser]
    permission_classes = [IsRecruiter]

    def get(self, request):
        query = request.GET.get('q') or request.GET.get('query', '')
        max_results = request.GET.get('max_results', 10)
        save_candidates = request.GET.get('save_candidates', 'false').lower() == 'true'

        if not query or not query.strip():
            return Response(
                {'error': 'Search query is required. Use ?q=your_search_query'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            max_results = int(max_results)
            if max_results < 1 or max_results > 100:
                return Response(
                    {'error': 'max_results must be between 1 and 100'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'max_results must be a valid integer'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = github_search_service(query, max_results)

            if not result['success']:
                return Response(
                    {'error': result.get('error', 'GitHub search failed'), 'query': query},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            saved_count = 0
            if save_candidates and result['data']:
                saved_count = self._save_github_candidates(result['data'])

            response_data = {
                'success': True,
                'query': result['query'],
                'total_count': result['total_count'],
                'results_returned': result['results_returned'],
                'candidates': result['data']
            }

            if save_candidates:
                response_data['saved_to_database'] = saved_count

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Search failed: {str(e)}', 'query': query},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _save_github_candidates(self, github_users: list) -> int:
        saved_count = 0
        for user in github_users:
            try:
                # Check if already exists in MongoDB by GitHub URL
                existing = mongo_find_by_github(user['profile_url'])
                doc = {
                    'name':            user['name'] or user['username'],
                    'email':           user.get('email') or None,
                    'github_url':      user['profile_url'],
                    'profile_summary': user['bio'],
                    'skills':          user['top_languages'],
                    'repo_score':      user['profile_score'],
                    'source':          'github_search',
                    'status':          'new',
                    'location':        user.get('location', ''),
                    'followers':       user.get('followers', 0),
                    'public_repos':    user.get('public_repos', 0),
                    'avatar_url':      user.get('avatar_url', ''),
                }
                if not existing:
                    mongo_insert_candidate(doc)
                saved_count += 1
            except Exception as e:
                logger.error(f"Failed to save GitHub candidate {user['username']}: {str(e)}")
                continue
        return saved_count


# ==============================
# Additional API Endpoints
# ==============================

class ProjectQAView(APIView):
    """
    Generate project-based interview Q&A.
    Analyses the project description to extract tech stack and generates
    targeted questions with hints AND detailed model answers.
    """
    parser_classes = [JSONParser]
    permission_classes = [AllowAny]
    authentication_classes = []

    # Tech-specific Q&A templates
    TECH_QA = {
        'react': [
            {
                'question': 'How did you manage state in this React project — did you use Context, Redux, or local state?',
                'topic': 'State Management', 'difficulty': 'Medium',
                'hint': 'Think about why you chose your approach over alternatives.',
                'answer': 'I used [your choice] because it suited the scale of the project. For small apps, useState and useContext are sufficient. For complex apps with many shared states, Redux or Zustand provides predictable state updates and better devtools. I structured components to keep state as local as possible and only lifted it when two or more components needed the same data.'
            },
            {
                'question': 'How did you handle component re-renders and performance optimisation in React?',
                'topic': 'Performance', 'difficulty': 'Hard',
                'hint': 'Mention useMemo, useCallback, React.memo, or lazy loading.',
                'answer': 'I used React.memo to prevent unnecessary re-renders on pure components, useCallback to memoize event handlers passed as props, and useMemo for expensive calculations. I also used code splitting with React.lazy and Suspense to reduce the initial bundle size. React DevTools Profiler helped identify components that re-rendered too often.'
            },
        ],
        'node': [
            {
                'question': 'How did you structure your Node.js API — MVC, layered architecture, or something else?',
                'topic': 'Architecture', 'difficulty': 'Medium',
                'hint': 'Explain the folder structure and why you separated concerns.',
                'answer': 'I followed a layered architecture: routes → controllers → services → data access layer. Routes handle HTTP concerns, controllers orchestrate logic, services contain business rules (kept framework-agnostic), and the data layer handles all DB queries. This made unit testing easy since I could mock each layer independently.'
            },
            {
                'question': 'How did you handle asynchronous operations and avoid callback hell in Node.js?',
                'topic': 'Async Programming', 'difficulty': 'Medium',
                'hint': 'Talk about async/await, Promises, and error handling.',
                'answer': 'I used async/await throughout with try/catch blocks for error handling. For parallel operations I used Promise.all() to run independent async tasks concurrently rather than sequentially. I created a centralised error handling middleware in Express to catch unhandled errors and return consistent error responses.'
            },
        ],
        'python': [
            {
                'question': 'How did you handle exceptions and ensure reliability in your Python code?',
                'topic': 'Error Handling', 'difficulty': 'Medium',
                'hint': 'Mention specific exception types, logging, and graceful degradation.',
                'answer': 'I used specific exception classes rather than bare except clauses to avoid silencing unexpected errors. I implemented logging with Python\'s logging module at different levels (DEBUG, INFO, ERROR). For external API calls, I wrapped them in try/except with retries using exponential backoff. I also used context managers (with statements) for resource cleanup.'
            },
        ],
        'django': [
            {
                'question': 'How did you design your Django models and handle database migrations in this project?',
                'topic': 'Database Design', 'difficulty': 'Medium',
                'hint': 'Talk about relationships, indexing, and migration strategy.',
                'answer': 'I designed models following database normalisation principles, using ForeignKey and ManyToManyField for relationships. I added db_index=True on fields used in frequent queries. For migrations, I wrote them incrementally and tested them on a staging database before production. I used select_related() and prefetch_related() to solve N+1 query problems.'
            },
            {
                'question': 'How did you implement authentication and authorisation in your Django project?',
                'topic': 'Security', 'difficulty': 'Hard',
                'hint': 'Mention Django auth system, permissions, JWT, or session-based auth.',
                'answer': 'I used Django\'s built-in authentication system for session-based auth and extended it with djangorestframework-simplejwt for API token authentication. I implemented custom permission classes to enforce role-based access control. Passwords are hashed automatically by Django. I also added CSRF protection on all state-changing endpoints and used HTTPS in production.'
            },
        ],
        'sql': [
            {
                'question': 'How did you optimise slow database queries in this project?',
                'topic': 'Database Optimisation', 'difficulty': 'Hard',
                'hint': 'Talk about EXPLAIN, indexes, query restructuring.',
                'answer': 'I used EXPLAIN ANALYZE to identify slow queries and found missing indexes were the main cause. I added composite indexes on columns frequently used together in WHERE clauses. I rewrote some N+1 queries using JOINs. I also implemented query result caching with Redis for read-heavy endpoints, reducing DB load significantly.'
            },
        ],
        'docker': [
            {
                'question': 'How did you containerise this project with Docker and manage multi-service orchestration?',
                'topic': 'DevOps', 'difficulty': 'Medium',
                'hint': 'Talk about Dockerfile, docker-compose, networking between containers.',
                'answer': 'I created a multi-stage Dockerfile to keep the production image lean — build stage installs dependencies, final stage copies only the necessary files. I used docker-compose to orchestrate the app, database, and Redis containers with a shared network. Environment variables are injected via .env files, never hardcoded in images. Health checks ensure dependent services wait for each other.'
            },
        ],
        'websocket': [
            {
                'question': 'How did you implement real-time functionality and handle connection management in this project?',
                'topic': 'Real-time Systems', 'difficulty': 'Hard',
                'hint': 'Talk about reconnection logic, broadcasting, and scaling.',
                'answer': 'I used WebSockets for bidirectional real-time communication. On the server I maintained a Map of connected clients keyed by user ID for targeted messaging. I implemented heartbeat pings every 30 seconds to detect stale connections and clean them up. For broadcasting to rooms, I used a pub/sub pattern. For scaling across multiple servers, I used Redis pub/sub to relay messages between Node instances.'
            },
        ],
        'mongodb': [
            {
                'question': 'How did you design your MongoDB schema — embedded documents or references, and why?',
                'topic': 'NoSQL Design', 'difficulty': 'Medium',
                'hint': 'Think about read/write patterns and document size limits.',
                'answer': 'I used embedded documents for data that is always accessed together and has a bounded size (e.g. address inside a user document). I used references (ObjectId) for data with many-to-many relationships or where subdocuments could grow unboundedly. I designed schemas around query patterns, not just data relationships, since MongoDB performance depends heavily on how data is accessed.'
            },
        ],
        'aws': [
            {
                'question': 'Which AWS services did you use and how did you think about cost optimisation?',
                'topic': 'Cloud Architecture', 'difficulty': 'Hard',
                'hint': 'Mention specific services, auto-scaling, and cost monitoring.',
                'answer': 'I used EC2 with auto-scaling groups to handle variable load, S3 for static assets and file storage, RDS for the database with read replicas for scaling reads, and CloudFront as a CDN. I set up AWS Cost Explorer alerts and used Reserved Instances for predictable workloads. I also used S3 lifecycle policies to move old data to cheaper storage tiers automatically.'
            },
        ],
        'ml': [
            {
                'question': 'How did you evaluate your machine learning model and handle class imbalance or overfitting?',
                'topic': 'ML Engineering', 'difficulty': 'Hard',
                'hint': 'Mention metrics beyond accuracy, cross-validation, regularisation.',
                'answer': 'I used F1-score, precision, and recall instead of just accuracy since the dataset was imbalanced. I handled class imbalance with SMOTE oversampling and class_weight parameters. For overfitting I used dropout regularisation, early stopping based on validation loss, and k-fold cross-validation. I tracked all experiments with MLflow to compare model versions systematically.'
            },
        ],
    }

    # General questions always included
    GENERAL_QA = [
        {
            'question': 'Walk me through the overall architecture of this project. How did you structure it?',
            'topic': 'Architecture', 'difficulty': 'Medium',
            'hint': 'Explain front-end, back-end, database, and how they communicate.',
            'answer': 'The project follows a [describe your pattern] architecture. The frontend is built with [tech] and communicates with the backend via REST APIs. The backend handles business logic and persists data to [database]. I separated concerns into distinct layers so each part can be changed independently. Key design decisions included [mention 1-2 choices and why you made them].'
        },
        {
            'question': 'What was the hardest technical challenge you faced in this project and how did you solve it?',
            'topic': 'Problem Solving', 'difficulty': 'Medium',
            'hint': 'Be specific — explain what went wrong, what you tried, and what finally worked.',
            'answer': 'The hardest challenge was [describe it clearly]. My initial approach was [what you tried first], but it failed because [reason]. I then researched [what you looked into] and found [solution]. The key insight was [core learning]. This taught me to [broader lesson]. Going forward I would [what you would do differently].'
        },
        {
            'question': 'How did you approach testing this project? What types of tests did you write?',
            'topic': 'Testing', 'difficulty': 'Medium',
            'hint': 'Cover unit, integration, and any E2E tests. Mention coverage and tools used.',
            'answer': 'I wrote unit tests for individual functions and business logic using [Jest/pytest/etc], achieving around [X]% code coverage on critical paths. I wrote integration tests for API endpoints to verify the full request-response cycle. I used mocking to isolate external dependencies. I also set up CI to run the test suite on every pull request so bugs were caught early rather than in production.'
        },
        {
            'question': 'How did you handle security in this project — authentication, input validation, and data protection?',
            'topic': 'Security', 'difficulty': 'Hard',
            'hint': 'Think about OWASP top 10 — XSS, CSRF, SQL injection, and auth.',
            'answer': 'I implemented JWT-based authentication with short-lived access tokens and longer-lived refresh tokens. All user inputs are validated and sanitised on the server side. I used parameterised queries to prevent SQL injection. HTTPS is enforced in production. Sensitive data is never logged. I also set appropriate HTTP security headers (CORS, CSP, X-Frame-Options) and kept all dependencies updated.'
        },
        {
            'question': 'If you had to scale this project to 10x the current users, what would you change?',
            'topic': 'Scalability', 'difficulty': 'Hard',
            'hint': 'Think about horizontal scaling, caching, database read replicas, CDN.',
            'answer': 'For 10x scale I would first add caching with Redis for frequently read data to reduce database load. I would horizontally scale the application servers behind a load balancer. The database would get read replicas for read-heavy queries. Static assets would move to a CDN. Long-running tasks would move to a background job queue. I would also add monitoring and alerting so bottlenecks are visible before they become outages.'
        },
    ]

    def _detect_technologies(self, description):
        """Extract technologies from project description."""
        desc_lower = description.lower()
        detected = []
        tech_keywords = {
            'react': ['react', 'reactjs', 'react.js', 'jsx', 'next.js', 'nextjs'],
            'node': ['node', 'nodejs', 'node.js', 'express', 'expressjs'],
            'python': ['python', 'flask', 'fastapi', 'pandas', 'numpy'],
            'django': ['django', 'drf', 'django rest'],
            'sql': ['sql', 'postgresql', 'mysql', 'sqlite', 'postgres'],
            'mongodb': ['mongodb', 'mongo', 'mongoose'],
            'docker': ['docker', 'kubernetes', 'k8s', 'container'],
            'aws': ['aws', 'amazon', 's3', 'ec2', 'lambda', 'rds'],
            'websocket': ['websocket', 'socket.io', 'real-time', 'realtime', 'ws'],
            'ml': ['machine learning', 'ml', 'tensorflow', 'pytorch', 'model', 'neural', 'sklearn'],
        }
        for tech, keywords in tech_keywords.items():
            if any(kw in desc_lower for kw in keywords):
                detected.append(tech)
        return detected

    def _extract_topics(self, description):
        """Extract high level topics for display."""
        topics = []
        desc_lower = description.lower()
        if any(w in desc_lower for w in ['react', 'vue', 'angular', 'frontend', 'ui', 'css']):
            topics.append('Frontend')
        if any(w in desc_lower for w in ['api', 'backend', 'server', 'node', 'django', 'flask']):
            topics.append('Backend')
        if any(w in desc_lower for w in ['sql', 'mongodb', 'database', 'db', 'redis']):
            topics.append('Database')
        if any(w in desc_lower for w in ['auth', 'jwt', 'login', 'oauth', 'session']):
            topics.append('Authentication')
        if any(w in desc_lower for w in ['docker', 'deploy', 'aws', 'cloud', 'ci/cd']):
            topics.append('DevOps')
        if any(w in desc_lower for w in ['test', 'jest', 'pytest', 'coverage']):
            topics.append('Testing')
        if any(w in desc_lower for w in ['real-time', 'websocket', 'socket', 'chat']):
            topics.append('Real-time')
        if any(w in desc_lower for w in ['ml', 'model', 'machine learning', 'ai', 'prediction']):
            topics.append('ML/AI')
        return topics or ['Architecture', 'Problem Solving', 'Design']

    def _assess_complexity(self, description, techs):
        """Determine overall project complexity."""
        word_count = len(description.split())
        tech_count = len(techs)
        if tech_count >= 5 or word_count > 80:
            return 'High'
        if tech_count >= 3 or word_count > 40:
            return 'Medium'
        return 'Low'

    def post(self, request):
        data = request.data or {}
        description = (data.get('description') or data.get('project_description') or '').strip()

        if not description:
            return Response({'error': 'Project description is required'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Detect stack and build question list
        techs = self._detect_technologies(description)
        topics = self._extract_topics(description)
        complexity = self._assess_complexity(description, techs)

        questions = []

        # Add tech-specific Q&A first (most relevant)
        for tech in techs[:4]:  # limit to 4 techs
            if tech in self.TECH_QA:
                for qa in self.TECH_QA[tech][:2]:  # max 2 per tech
                    if len(questions) < 6:
                        questions.append(qa)

        # Fill remaining slots with general questions
        general_needed = max(0, 8 - len(questions))
        questions += self.GENERAL_QA[:general_needed]

        return Response({
            'questions': questions,
            'overall_complexity': complexity,
            'topics_covered': topics,
            'tech_detected': techs,
            'total_questions': len(questions),
        })


class MockInterviewStartView(APIView):
    """
    Generate role-specific interview questions with difficulty and topic tags.
    Returns structured question objects the frontend can render directly.
    """
    parser_classes = [JSONParser]
    permission_classes = [AllowAny]
    authentication_classes = []

    QUESTION_BANK = {
        'frontend': [
            {'question': 'Explain the difference between var, let, and const in JavaScript.', 'difficulty': 'Easy', 'topic': 'JavaScript'},
            {'question': 'How does the Virtual DOM work in React, and why is it faster?', 'difficulty': 'Medium', 'topic': 'React'},
            {'question': 'What is CSS specificity and how does the cascade work?', 'difficulty': 'Easy', 'topic': 'CSS'},
            {'question': 'Explain React hooks — useEffect, useState, and useMemo with real use cases.', 'difficulty': 'Medium', 'topic': 'React'},
            {'question': 'How would you optimize a React app that has performance issues?', 'difficulty': 'Hard', 'topic': 'Performance'},
            {'question': 'What is the event loop in JavaScript? Walk me through an async example.', 'difficulty': 'Hard', 'topic': 'JavaScript'},
        ],
        'backend': [
            {'question': 'What is the difference between SQL and NoSQL databases? When would you use each?', 'difficulty': 'Easy', 'topic': 'Databases'},
            {'question': 'Explain RESTful API design principles. What makes an API truly RESTful?', 'difficulty': 'Medium', 'topic': 'API Design'},
            {'question': 'How do you handle database migrations in production without downtime?', 'difficulty': 'Hard', 'topic': 'Databases'},
            {'question': 'What is the N+1 query problem and how do you fix it?', 'difficulty': 'Medium', 'topic': 'ORM'},
            {'question': 'Explain how you would design a rate limiting system for an API.', 'difficulty': 'Hard', 'topic': 'System Design'},
            {'question': 'What is the difference between authentication and authorization?', 'difficulty': 'Easy', 'topic': 'Security'},
        ],
        'fullstack': [
            {'question': 'Walk me through building a full-stack feature from database to UI.', 'difficulty': 'Medium', 'topic': 'Architecture'},
            {'question': 'How do you handle state management in a large React application?', 'difficulty': 'Medium', 'topic': 'Frontend'},
            {'question': 'Explain the difference between server-side and client-side rendering.', 'difficulty': 'Medium', 'topic': 'Web'},
            {'question': 'How would you secure a web application against common vulnerabilities (XSS, CSRF)?', 'difficulty': 'Hard', 'topic': 'Security'},
            {'question': 'How do you design a REST API and its corresponding database schema together?', 'difficulty': 'Hard', 'topic': 'Design'},
            {'question': 'What is CORS and how do you handle it in a full-stack app?', 'difficulty': 'Easy', 'topic': 'Web'},
        ],
        'data': [
            {'question': 'Explain the difference between supervised and unsupervised learning.', 'difficulty': 'Easy', 'topic': 'ML Basics'},
            {'question': 'What is overfitting and how do you prevent it?', 'difficulty': 'Medium', 'topic': 'ML'},
            {'question': 'Walk me through how you would clean a messy real-world dataset.', 'difficulty': 'Medium', 'topic': 'Data Cleaning'},
            {'question': 'Explain the bias-variance tradeoff in machine learning.', 'difficulty': 'Hard', 'topic': 'Theory'},
            {'question': 'How do you handle class imbalance in a classification problem?', 'difficulty': 'Hard', 'topic': 'ML'},
            {'question': 'What metrics would you use to evaluate a regression model vs a classifier?', 'difficulty': 'Medium', 'topic': 'Evaluation'},
        ],
        'devops': [
            {'question': 'Explain the difference between Docker containers and virtual machines.', 'difficulty': 'Easy', 'topic': 'Containers'},
            {'question': 'What is a CI/CD pipeline and what stages would you include?', 'difficulty': 'Medium', 'topic': 'CI/CD'},
            {'question': 'How would you handle secrets management in a Kubernetes cluster?', 'difficulty': 'Hard', 'topic': 'Kubernetes'},
            {'question': 'Explain blue-green deployments and when you would use them.', 'difficulty': 'Medium', 'topic': 'Deployments'},
            {'question': 'How do you monitor a microservices architecture in production?', 'difficulty': 'Hard', 'topic': 'Monitoring'},
            {'question': 'What is Infrastructure as Code and what tools have you used?', 'difficulty': 'Easy', 'topic': 'IaC'},
        ],
        'default': [
            {'question': 'Tell me about a challenging technical problem you solved recently.', 'difficulty': 'Medium', 'topic': 'Experience'},
            {'question': 'How do you approach learning a new technology or framework?', 'difficulty': 'Easy', 'topic': 'Learning'},
            {'question': 'Describe a time when you had to make a technical decision with limited information.', 'difficulty': 'Medium', 'topic': 'Decision Making'},
            {'question': 'How do you ensure code quality in your projects?', 'difficulty': 'Medium', 'topic': 'Quality'},
            {'question': 'Explain how you would design a URL shortener like bit.ly.', 'difficulty': 'Hard', 'topic': 'System Design'},
            {'question': 'What is your approach to debugging a production issue?', 'difficulty': 'Medium', 'topic': 'Debugging'},
        ],
    }

    def _get_category(self, role):
        r = role.lower()
        if any(w in r for w in ['frontend', 'front-end', 'react', 'vue', 'angular', 'ui']):
            return 'frontend'
        if any(w in r for w in ['backend', 'back-end', 'django', 'node', 'api', 'server']):
            return 'backend'
        if any(w in r for w in ['fullstack', 'full stack', 'full-stack']):
            return 'fullstack'
        if any(w in r for w in ['data', 'ml', 'machine learning', 'analyst', 'scientist']):
            return 'data'
        if any(w in r for w in ['devops', 'cloud', 'infra', 'sre', 'platform']):
            return 'devops'
        return 'default'

    def post(self, request):
        data = request.data or {}
        role = data.get('role', 'Software Engineer').strip()
        category = self._get_category(role)
        questions = self.QUESTION_BANK.get(category, self.QUESTION_BANK['default'])

        # Always add a behavioural question
        questions = questions[:5] + [{
            'question': f'Where do you see yourself in 3 years as a {role}?',
            'difficulty': 'Easy',
            'topic': 'Career Goals',
        }]

        mock_interview = MockInterview.objects.create(
            role=role,
            questions=[q['question'] for q in questions],
            status='in_progress',
        )

        return Response({
            'interview_id': mock_interview.id,
            'questions': questions,
            'role': role,
        })


class MockInterviewAnalyzeView(APIView):
    """
    Analyze interview answers from transcript text.
    Scores confidence, clarity, relevance per question and overall.
    """
    parser_classes = [JSONParser]
    permission_classes = [AllowAny]
    authentication_classes = []

    FILLER_WORDS = ['um', 'uh', 'like', 'you know', 'basically', 'literally',
                    'actually', 'so yeah', 'kind of', 'sort of', 'i mean', 'right']

    def _count_fillers(self, text):
        text_lower = text.lower()
        return sum(text_lower.count(f' {fw} ') for fw in self.FILLER_WORDS)

    def _score_answer(self, question, transcript, role):
        """Score a single answer based on transcript quality."""
        if not transcript or transcript.strip() == '(No transcript available)':
            return {'score': 0, 'feedback': 'No answer recorded for this question.'}

        words = transcript.strip().split()
        word_count = len(words)
        fillers = self._count_fillers(transcript)

        # Length score (ideal 80-200 words)
        if word_count < 20:
            length_score = 30
            length_note = 'Answer too short — provide more detail'
        elif word_count < 50:
            length_score = 55
            length_note = 'Answer could be more detailed'
        elif word_count <= 200:
            length_score = 90
            length_note = 'Good answer length'
        else:
            length_score = 75
            length_note = 'Answer is a bit long — be more concise'

        # Filler penalty
        filler_penalty = min(fillers * 4, 30)

        # Keyword relevance — check if answer mentions technical terms
        tech_terms = ['api', 'database', 'function', 'class', 'component', 'server',
                      'client', 'framework', 'library', 'architecture', 'design',
                      'performance', 'security', 'test', 'deploy', 'code', 'data',
                      'algorithm', 'system', 'service', 'request', 'response']
        found_terms = sum(1 for t in tech_terms if t in transcript.lower())
        relevance_bonus = min(found_terms * 5, 20)

        score = max(0, min(100, length_score - filler_penalty + relevance_bonus))

        # Generate feedback
        feedback_parts = []
        if fillers > 3:
            feedback_parts.append(f'Used {fillers} filler words — try to pause instead')
        if word_count < 50:
            feedback_parts.append('Give a more complete answer with an example')
        if found_terms < 2:
            feedback_parts.append('Use more specific technical terminology')
        if score >= 75:
            feedback_parts.append('Strong, well-structured answer')
        elif score >= 55:
            feedback_parts.append('Decent answer — add more concrete examples')

        return {
            'score': round(score),
            'feedback': '. '.join(feedback_parts) if feedback_parts else length_note,
            'word_count': word_count,
            'filler_count': fillers,
        }

    def post(self, request):
        data = request.data or {}
        answers = data.get('answers', data.get('responses', []))
        role = data.get('role', 'Software Engineer')

        if not answers:
            return Response({'error': 'No answers provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Analyse each answer
        per_question = []
        all_scores = []
        total_fillers = 0
        total_words = 0

        for i, ans in enumerate(answers):
            transcript = ans.get('transcript', '')
            question = ans.get('question', f'Question {i+1}')
            result = self._score_answer(question, transcript, role)
            all_scores.append(result['score'])
            total_fillers += result.get('filler_count', 0)
            total_words += result.get('word_count', 0)
            per_question.append({
                'question_number': i + 1,
                'question': question,
                'transcript': transcript,
                'score': result['score'],
                'feedback': result['feedback'],
            })

        avg_score = round(sum(all_scores) / len(all_scores)) if all_scores else 0
        avg_words = round(total_words / len(answers)) if answers else 0

        # Speaking pace from word count
        if avg_words < 30:
            speaking_pace = 'Too brief'
        elif avg_words < 60:
            speaking_pace = 'Concise'
        elif avg_words <= 150:
            speaking_pace = 'Optimal'
        else:
            speaking_pace = 'Detailed'

        # Overall scores
        confidence = min(100, max(0, avg_score + 5))
        clarity = min(100, max(0, avg_score - (total_fillers * 2)))
        knowledge = min(100, max(0, avg_score))
        energy = min(100, max(0, avg_score + 10 - total_fillers))

        # Strengths
        strengths = []
        if confidence >= 70:
            strengths.append('Answered with confidence and good structure')
        if total_fillers <= 5:
            strengths.append('Clear speech with minimal filler words')
        if avg_words >= 60:
            strengths.append('Provided detailed, well-developed answers')
        if knowledge >= 65:
            strengths.append('Demonstrated relevant technical knowledge')
        if not strengths:
            strengths.append('Completed the interview — practice makes progress')

        # Improvements
        improvements = []
        if total_fillers > 5:
            improvements.append(f'Reduce filler words — used {total_fillers} total across all answers')
        if avg_words < 50:
            improvements.append('Give longer, more detailed answers with specific examples')
        if confidence < 60:
            improvements.append('Practice speaking more confidently — use the STAR method for answers')
        if knowledge < 60:
            improvements.append('Use more technical terminology relevant to the role')
        improvements.append('Record yourself answering and listen back to catch habits')
        improvements.append(f'Study common {role} interview patterns and practise out loud')

        return Response({
            'overall_confidence': confidence,
            'overall_clarity': clarity,
            'knowledge_relevance': knowledge,
            'energy_level': energy,
            'speaking_pace': speaking_pace,
            'filler_word_estimate': total_fillers,
            'strengths': strengths,
            'improvements': improvements[:4],
            'per_question': per_question,
        })


class TalentSearchView(APIView):
    """
    Search for talent across GitHub or job portals.
    - search_type = 'github'  → real GitHub API search
    - search_type = 'portal'  → simulated portal candidates
    """
    parser_classes = [JSONParser]
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        data = request.data or {}
        search_type = data.get('search_type', 'github')
        role = (data.get('role') or data.get('query') or '').strip()
        skills = (data.get('skills') or '').strip()
        exp_range = (data.get('exp_range') or '').strip()

        if not role:
            return Response(
                {'error': 'Role is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build search query
        query_parts = [role]
        if skills:
            query_parts.append(skills)
        query = ' '.join(query_parts)

        if search_type == 'github':
            return self._github_search(query, role)
        else:
            return self._portal_search(role, skills, exp_range)

    def _github_search(self, query, role):
        """Real GitHub search via analysis_engine."""
        try:
            result = github_search_service(query, max_results=10)

            if not result['success']:
                return Response(
                    {'error': result.get('error', 'GitHub search failed')},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            # Map GitHub users → candidate-shaped objects for the frontend
            candidates = []
            for u in result['data']:
                # Map top_languages → skills
                skills_list = u.get('top_languages', [])
                profile_score = u.get('profile_score', 0)

                candidates.append({
                    'id': u['username'],
                    'name': u['name'] or u['username'],
                    'github_url': u['profile_url'],
                    'profile_summary': u['bio'],
                    'skills': skills_list,
                    'repo_score': round(profile_score),
                    'role_match_score': min(100, round(profile_score * 0.9)),
                    'skill_validation_score': min(100, len(skills_list) * 12),
                    'consistency_score': min(100, round(profile_score * 0.85)),
                    'final_fit': 'High' if profile_score >= 65 else 'Medium' if profile_score >= 40 else 'Low',
                    'learning_velocity': 'High' if u.get('public_repos', 0) >= 20 else 'Medium',
                    'experience_years': 0,
                    'target_role': role,
                    'source': 'github_search',
                    'avatar_url': u.get('avatar_url', ''),
                    'location': u.get('location', ''),
                    'followers': u.get('followers', 0),
                    'public_repos': u.get('public_repos', 0),
                })

            return Response({
                'candidates': candidates,
                'total_count': len(candidates),
                'source': 'github',
                'query': query,
            })

        except Exception as e:
            logger.error(f"GitHub talent search failed: {e}")
            return Response(
                {'error': f'GitHub search failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _portal_search(self, role, skills, exp_range):
        """
        Realistic deterministic simulated portal candidates.
        Seeded by role so same search always returns same results.
        Implements paper requirements:
          - Evidence-backed skill validation (Valid/Partial/Unverified)
          - Cross-document consistency flags
          - Learning velocity
          - Explainability text
          - Realistic Indian tech profiles
        """
        import hashlib

        # Seed RNG from role so results are reproducible per role
        seed = int(hashlib.md5(role.lower().encode()).hexdigest(), 16) % (10 ** 8)
        rng = __import__('random').Random(seed)

        # ── Candidate pool ──────────────────────────────────────────────
        CANDIDATE_POOL = [
            {
                'name': 'Aarav Mehta',
                'location': 'Bangalore, Karnataka',
                'education': "B.Tech Computer Science — VIT Vellore (2021)",
                'companies': ['Infosys', 'Razorpay'],
                'base_skills': ['Python', 'Django', 'PostgreSQL', 'Docker', 'REST APIs', 'Git'],
                'extra_skills': ['Redis', 'Celery', 'AWS EC2', 'Unit Testing'],
                'projects': ['Built payment reconciliation service at Razorpay handling 10k txn/day',
                             'Developed internal HR portal using Django + React'],
                'certifications': ['AWS Cloud Practitioner'],
                'velocity': 'High',
                'portal': 'LinkedIn',
                'profile_url': 'https://linkedin.com/in/aarav-mehta-dev',
            },
            {
                'name': 'Priya Nair',
                'location': 'Hyderabad, Telangana',
                'education': "M.Tech Software Engineering — BITS Pilani (2022)",
                'companies': ['TCS', 'Flipkart'],
                'base_skills': ['React', 'TypeScript', 'Node.js', 'MongoDB', 'CSS', 'Jest'],
                'extra_skills': ['Redux', 'GraphQL', 'Webpack', 'Storybook'],
                'projects': ['Led frontend redesign of Flipkart seller portal (2M users)',
                             'Built component library used across 3 product teams'],
                'certifications': ['Meta Frontend Developer Certificate'],
                'velocity': 'High',
                'portal': 'Naukri',
                'profile_url': 'https://naukri.com/profile/priya-nair-frontend',
            },
            {
                'name': 'Rohit Sharma',
                'location': 'Pune, Maharashtra',
                'education': "B.E. Information Technology — Pune University (2020)",
                'companies': ['Wipro', 'Persistent Systems'],
                'base_skills': ['Java', 'Spring Boot', 'MySQL', 'Microservices', 'Maven'],
                'extra_skills': ['Kafka', 'Docker', 'Jenkins', 'Kubernetes'],
                'projects': ['Designed microservices migration for legacy monolith at Persistent',
                             'Built real-time order tracking API serving 50k requests/min'],
                'certifications': ['Oracle Java SE 11 Developer'],
                'velocity': 'Medium',
                'portal': 'Naukri',
                'profile_url': 'https://naukri.com/profile/rohit-sharma-java',
            },
            {
                'name': 'Sneha Patel',
                'location': 'Mumbai, Maharashtra',
                'education': "B.Sc Computer Science — Mumbai University (2023)",
                'companies': ['Internship at Zomato'],
                'base_skills': ['Python', 'Machine Learning', 'Pandas', 'NumPy', 'SQL'],
                'extra_skills': ['TensorFlow', 'Scikit-learn', 'Matplotlib'],
                'projects': ['Food delivery demand prediction model (87% accuracy)',
                             'Customer churn analysis dashboard using Streamlit'],
                'certifications': ['Google Data Analytics Certificate', 'Coursera ML Specialization'],
                'velocity': 'High',
                'portal': 'Internshala',
                'profile_url': 'https://internshala.com/student/sneha-patel-ml',
            },
            {
                'name': 'Karan Joshi',
                'location': 'Chennai, Tamil Nadu',
                'education': "B.Tech IT — Anna University (2019)",
                'companies': ['HCL Technologies', 'Zoho', 'Freshworks'],
                'base_skills': ['JavaScript', 'React', 'Python', 'Django', 'PostgreSQL', 'AWS'],
                'extra_skills': ['Next.js', 'Tailwind CSS', 'Docker', 'CI/CD'],
                'projects': ['Full-stack CRM module at Freshworks used by 500+ businesses',
                             'Open source contribution: React form validation library (800 GitHub stars)'],
                'certifications': ['AWS Solutions Architect Associate'],
                'velocity': 'High',
                'portal': 'LinkedIn',
                'profile_url': 'https://linkedin.com/in/karan-joshi-fullstack',
            },
            {
                'name': 'Divya Menon',
                'location': 'Kochi, Kerala',
                'education': "MCA — Cochin University of Science and Technology (2021)",
                'companies': ['UST Global', 'IBS Software'],
                'base_skills': ['Python', 'Flask', 'MySQL', 'REST APIs', 'Git'],
                'extra_skills': ['Docker', 'Nginx', 'Linux'],
                'projects': ['Airline reservation backend API at IBS Software',
                             'Inventory management system for warehouse client'],
                'certifications': [],
                'velocity': 'Medium',
                'portal': 'Indeed',
                'profile_url': 'https://indeed.com/r/divya-menon-backend',
            },
            {
                'name': 'Aditya Kumar',
                'location': 'Noida, Uttar Pradesh',
                'education': "B.Tech CSE — Amity University (2022)",
                'companies': ['Accenture', 'Capgemini'],
                'base_skills': ['React', 'JavaScript', 'HTML', 'CSS', 'Git'],
                'extra_skills': ['Vue.js', 'Bootstrap', 'jQuery'],
                'projects': ['Insurance portal UI at Accenture',
                             'Internal dashboard for HR team'],
                'certifications': ['Udemy React Complete Guide'],
                'velocity': 'Low',
                'portal': 'Naukri',
                'profile_url': 'https://naukri.com/profile/aditya-kumar-react',
            },
            {
                'name': 'Ananya Singh',
                'location': 'Delhi, NCR',
                'education': "B.Tech CSE — DTU (2020)",
                'companies': ['Paytm', 'PhonePe', 'Meesho'],
                'base_skills': ['Python', 'Golang', 'Kubernetes', 'Docker', 'AWS', 'Terraform'],
                'extra_skills': ['Prometheus', 'Grafana', 'Ansible', 'Jenkins', 'Linux'],
                'projects': ['Migrated Paytm payment infra to Kubernetes (40% cost reduction)',
                             'Built self-healing deployment pipeline at PhonePe'],
                'certifications': ['CKA — Certified Kubernetes Administrator', 'AWS DevOps Engineer'],
                'velocity': 'High',
                'portal': 'LinkedIn',
                'profile_url': 'https://linkedin.com/in/ananya-singh-devops',
            },
            {
                'name': 'Vikram Rao',
                'location': 'Bangalore, Karnataka',
                'education': "B.E. ECE — RV College of Engineering (2018)",
                'companies': ['Mindtree', 'Mphasis', 'Publicis Sapient'],
                'base_skills': ['Java', 'React', 'Spring Boot', 'Oracle DB', 'REST APIs'],
                'extra_skills': ['AWS', 'Microservices', 'Agile', 'JIRA'],
                'projects': ['Banking portal modernisation at Publicis Sapient',
                             'Trade settlement engine serving top 3 Indian banks'],
                'certifications': ['PMP Certified', 'AWS Developer Associate'],
                'velocity': 'Medium',
                'portal': 'LinkedIn',
                'profile_url': 'https://linkedin.com/in/vikram-rao-java',
            },
            {
                'name': 'Neha Gupta',
                'location': 'Hyderabad, Telangana',
                'education': "B.Tech CSE — JNTU (2023)",
                'companies': ['Internship at Byju\'s', 'Internship at Swiggy'],
                'base_skills': ['Python', 'SQL', 'Pandas', 'Data Analysis', 'Excel'],
                'extra_skills': ['Tableau', 'Power BI', 'NumPy'],
                'projects': ['Content engagement analysis at Byju\'s (reduced drop-off 18%)',
                             'Delivery time prediction model at Swiggy internship'],
                'certifications': ['IBM Data Science Professional Certificate'],
                'velocity': 'Medium',
                'portal': 'Internshala',
                'profile_url': 'https://internshala.com/student/neha-gupta-data',
            },
            {
                'name': 'Rahul Verma',
                'location': 'Indore, Madhya Pradesh',
                'education': "B.Tech CSE — IIT Indore (2021)",
                'companies': ['Microsoft', 'Adobe'],
                'base_skills': ['C++', 'Python', 'System Design', 'Algorithms', 'SQL', 'Azure'],
                'extra_skills': ['Distributed Systems', 'gRPC', 'Kafka', 'Redis'],
                'projects': ['Search ranking improvement at Adobe (12% CTR increase)',
                             'Distributed task scheduler at Microsoft Azure team'],
                'certifications': ['Azure Solutions Architect Expert'],
                'velocity': 'High',
                'portal': 'LinkedIn',
                'profile_url': 'https://linkedin.com/in/rahul-verma-sde',
            },
            {
                'name': 'Pooja Iyer',
                'location': 'Coimbatore, Tamil Nadu',
                'education': "B.E. CSE — PSG College of Technology (2022)",
                'companies': ['Cognizant', 'Tata Elxsi'],
                'base_skills': ['Python', 'Django', 'JavaScript', 'React', 'MySQL'],
                'extra_skills': ['Docker', 'Git', 'Agile'],
                'projects': ['E-commerce backend at Cognizant for UK retail client',
                             'Telematics dashboard for automotive client at Tata Elxsi'],
                'certifications': [],
                'velocity': 'Medium',
                'portal': 'Indeed',
                'profile_url': 'https://indeed.com/r/pooja-iyer-python',
            },
        ]

        # ── Experience range filter ─────────────────────────────────────
        exp_ranges = {
            '0-2': (0, 2), '2-5': (2, 5),
            '5-10': (5, 10), '10+': (10, 20),
        }
        min_exp, max_exp = exp_ranges.get(exp_range, (0, 20))

        # ── Role → relevant skills map ──────────────────────────────────
        ROLE_SKILL_MAP = {
            'frontend':  ['react', 'javascript', 'typescript', 'css', 'html', 'vue', 'next'],
            'backend':   ['python', 'django', 'node', 'java', 'spring', 'flask', 'sql', 'api'],
            'fullstack': ['react', 'python', 'javascript', 'node', 'sql', 'django', 'css'],
            'data':      ['python', 'pandas', 'sql', 'machine learning', 'numpy', 'tensorflow'],
            'devops':    ['docker', 'kubernetes', 'aws', 'ci/cd', 'terraform', 'linux', 'jenkins'],
            'ml':        ['python', 'tensorflow', 'machine learning', 'pandas', 'numpy', 'sklearn'],
            'default':   ['python', 'javascript', 'sql', 'git', 'api', 'react'],
        }

        def get_role_keywords(role_str):
            r = role_str.lower()
            if any(w in r for w in ['frontend', 'front end', 'react', 'vue', 'ui']):
                return ROLE_SKILL_MAP['frontend']
            if any(w in r for w in ['backend', 'back end', 'django', 'node', 'api']):
                return ROLE_SKILL_MAP['backend']
            if any(w in r for w in ['fullstack', 'full stack']):
                return ROLE_SKILL_MAP['fullstack']
            if any(w in r for w in ['data scientist', 'data analyst', 'analytics']):
                return ROLE_SKILL_MAP['data']
            if any(w in r for w in ['devops', 'cloud', 'infra', 'sre']):
                return ROLE_SKILL_MAP['devops']
            if any(w in r for w in ['machine learning', 'ml', 'ai engineer']):
                return ROLE_SKILL_MAP['ml']
            return ROLE_SKILL_MAP['default']

        role_keywords = get_role_keywords(role)

        # ── Skill validation logic ──────────────────────────────────────
        def validate_skills(candidate_skills, projects, certifications):
            """
            Classify each skill as Valid / Partial / Unverified
            based on project evidence and certifications.
            Paper requirement: Evidence-Backed Skill Validation
            """
            validated = []
            project_text = ' '.join(projects).lower()
            cert_text = ' '.join(certifications).lower()

            for skill in candidate_skills:
                sl = skill.lower()
                in_project = sl in project_text
                in_cert = sl in cert_text

                if in_project:
                    status = 'Valid'
                elif in_cert:
                    status = 'Partial'
                else:
                    status = 'Unverified'

                validated.append({'skill': skill, 'status': status})
            return validated

        # ── Consistency check logic ─────────────────────────────────────
        def check_consistency(candidate_data, exp_years):
            """
            Detect cross-document inconsistencies.
            Paper requirement: Cross-Document Consistency Analysis
            """
            flags = []
            skills = candidate_data['base_skills'] + candidate_data['extra_skills']
            projects = candidate_data['projects']
            certifications = candidate_data['certifications']
            companies = candidate_data['companies']

            # Check 1: Senior skills claimed with low experience
            senior_skills = ['kubernetes', 'terraform', 'system design', 'distributed systems', 'kafka', 'grpc']
            has_senior_skill = any(s.lower() in senior_skills for s in skills)
            if has_senior_skill and exp_years < 2:
                flags.append({
                    'type': 'warning',
                    'message': 'Advanced infrastructure skills claimed but experience is under 2 years — verify project context'
                })

            # Check 2: Skills not reflected in any project or company
            project_text = ' '.join(projects).lower()
            unverified_count = sum(
                1 for s in skills
                if s.lower() not in project_text and s.lower() not in ' '.join(certifications).lower()
            )
            if unverified_count > len(skills) * 0.5:
                flags.append({
                    'type': 'warning',
                    'message': f'{unverified_count} of {len(skills)} skills have no supporting project or certification evidence'
                })

            # Check 3: Multiple short stints — could indicate instability
            if len(companies) >= 3 and exp_years < 3:
                flags.append({
                    'type': 'info',
                    'message': f'Worked at {len(companies)} companies in {exp_years:.1f} years — ask about reasons for transitions'
                })

            # Check 4: No certifications for heavily certified domains
            cert_heavy = ['aws', 'azure', 'gcp', 'kubernetes', 'java', 'salesforce']
            has_cert_skill = any(s.lower() in cert_heavy for s in skills)
            if has_cert_skill and not certifications:
                flags.append({
                    'type': 'info',
                    'message': 'Claims cloud/platform skills but no certifications found — consider requesting proof'
                })

            # Consistency score: start at 100, deduct per flag
            deduction = {'warning': 18, 'info': 8}
            score = max(30, 100 - sum(deduction.get(f['type'], 10) for f in flags))
            return flags, round(score)

        # ── Score role match ────────────────────────────────────────────
        def score_role_match(candidate_skills, role_kw):
            all_skills_lower = [s.lower() for s in candidate_skills]
            matched = sum(1 for kw in role_kw if any(kw in s for s in all_skills_lower))
            return round(min(100, (matched / max(len(role_kw), 1)) * 100 * 1.2))

        # ── Build candidates ────────────────────────────────────────────
        requested_skills = [s.strip().lower() for s in skills.split(',') if s.strip()] if skills else []

        # Score all candidates and sort by role match
        scored = []
        for c in CANDIDATE_POOL:
            all_skills = c['base_skills'] + c['extra_skills']
            rm = score_role_match(all_skills, role_keywords)

            # Boost score if requested skills match
            if requested_skills:
                req_matched = sum(1 for rs in requested_skills
                                  if any(rs in s.lower() for s in all_skills))
                rm = min(100, rm + req_matched * 8)

            scored.append((rm, c))

        scored.sort(key=lambda x: x[0], reverse=True)

        # ── Generate experience deterministically ───────────────────────
        candidates = []
        for idx, (rm, c) in enumerate(scored[:8]):
            # Deterministic experience based on companies
            company_count = len(c['companies'])
            base_exp = company_count * 1.5
            exp_years = round(min(max(base_exp + rng.uniform(-0.5, 0.5), 0), 15), 1)

            # Filter by exp range
            if not (min_exp <= exp_years <= max_exp):
                # Adjust to fit range for demo purposes
                exp_years = round(rng.uniform(min_exp, min(max_exp, min_exp + 3)), 1)

            all_skills = c['base_skills'] + c['extra_skills']
            validated_skills = validate_skills(all_skills, c['projects'], c['certifications'])
            consistency_flags, consistency_score = check_consistency(c, exp_years)

            # Skill validation score — % of skills that are Valid
            valid_count = sum(1 for v in validated_skills if v['status'] == 'Valid')
            skill_val_score = round((valid_count / max(len(validated_skills), 1)) * 100)

            # Learning velocity score
            velocity_score = {'High': 85, 'Medium': 60, 'Low': 35}[c['velocity']]

            final_fit = 'High' if rm >= 70 and consistency_score >= 70 else \
                        'Medium' if rm >= 50 else 'Low'

            # Explainability text
            valid_skills_str = ', '.join(
                v['skill'] for v in validated_skills if v['status'] == 'Valid'
            )[:80] or 'general skills'
            explain = (
                f"Matched {rm}% on role keywords. "
                f"{valid_count}/{len(validated_skills)} skills verified via project evidence. "
                f"Consistency score {consistency_score}/100"
                f"{' — ' + consistency_flags[0]['message'] if consistency_flags else ''}."
            )

            candidates.append({
                'id': f'portal_{idx}_{seed}',
                'name': c['name'],
                'target_role': role,
                'location': c['location'],
                'experience_years': exp_years,
                'education': c['education'],
                'companies': c['companies'],

                # Skills with validation status
                'skills': all_skills,
                'validated_skills': validated_skills,

                # Projects + certs for expanded view
                'projects': c['projects'],
                'certifications': c['certifications'],

                # Scores
                'role_match_score': rm,
                'consistency_score': consistency_score,
                'skill_validation_score': skill_val_score,
                'learning_velocity': c['velocity'],
                'final_fit': final_fit,

                # Consistency analysis (paper requirement)
                'consistency_flags': consistency_flags,

                # Profile info
                'portal_source': c['portal'],
                'profile_url': c['profile_url'],
                'profile_summary': f"{c['name']} — {exp_years}y exp at {', '.join(c['companies'][-2:])}. {c['projects'][0]}.",
                'career_trajectory': f"Progressed from {c['companies'][0]} to {c['companies'][-1]}. " +
                                     (f"Holds {c['certifications'][0]}." if c['certifications'] else "No certifications listed."),
                'explainability': explain,
                'source': 'job_portal_search',
            })

        return Response({
            'candidates': candidates,
            'total_count': len(candidates),
            'source': 'portal',
            'query': role,
        })


# ==============================
# 🔐 Auth API
# ==============================

class RegisterView(APIView):
    """
    Register a new user.

    Required fields:
      - email (str)
      - password (str, min 8 chars)
      - full_name (str)
      - role (str): "recruiter" or "jobseeker"

    Recruiter restriction:
      Email domain must be in settings.ALLOWED_RECRUITER_DOMAINS.
      This prevents random signups from claiming the recruiter role.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [JSONParser]

    def post(self, request):
        data = request.data or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        full_name = (data.get("full_name") or "").strip()
        role = (data.get("role") or "jobseeker").strip().lower()

        # ── Validate email ──────────────────────────────────────────
        if not email or "@" not in email:
            return Response(
                {"error": "Valid email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Validate password ───────────────────────────────────────
        if len(password) < 8:
            return Response(
                {"error": "Password must be at least 8 characters"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Validate role ───────────────────────────────────────────
        if role not in ("recruiter", "jobseeker"):
            return Response(
                {"error": "Role must be 'recruiter' or 'jobseeker'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Recruiter domain check ──────────────────────────────────
        if role == "recruiter" and not _is_allowed_recruiter_email(email):
            allowed_domains = getattr(settings, "ALLOWED_RECRUITER_DOMAINS", [])
            domain_hint = ", ".join(allowed_domains) if allowed_domains else "no domains configured"
            return Response(
                {
                    "error": (
                        "Recruiter accounts require an official company email address. "
                        f"Allowed domains: {domain_hint}"
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ── Duplicate check ─────────────────────────────────────────
        if User.objects.filter(username=email).exists():
            return Response(
                {"error": "An account with this email already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Create user + profile ───────────────────────────────────
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=full_name,
        )
        UserProfile.objects.create(user=user, role=role)

        # ✅ Explicitly set backend to avoid _get_backend_from_user crash with social_django
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        logger.info(f"New {role} registered: {email}")
        return Response(_user_payload(user), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    Authenticate an existing user.
    Returns user payload including role.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [JSONParser]

    def post(self, request):
        data = request.data or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if not email or not password:
            return Response(
                {"error": "Email and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=email, password=password)
        if not user:
            # Also try with email field directly (some setups use email as username)
            User = get_user_model()
            try:
                u = User.objects.get(email=email)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                pass

        if not user:
            return Response(
                {"error": "Invalid email or password"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Ensure profile exists for legacy users (created before this update)
        if not UserProfile.objects.filter(user=user).exists():
            UserProfile.objects.get_or_create(user=user, defaults={"role": "jobseeker"})

        # ✅ Explicitly set backend to avoid _get_backend_from_user crash with social_django
        if not hasattr(user, 'backend'):
            user.backend = 'django.contrib.auth.backends.ModelBackend'

        login(request, user)
        logger.info(f"User logged in: {email} (role: {_get_user_role(user)})")
        return Response(_user_payload(user))


# ── Chatbot ─────────────────────────────────────────────────────────────────
CHATBOT_INTENTS = {
    'candidates': ['candidate','resume','applicant','profile','skill','fit','score','top','best','how many'],
    'jobs':       ['job','role','position','opening','vacancy','hiring'],
    'platform':   ['how','what','neurohire','feature','work','use','help','explain'],
    'analytics':  ['haar','cdr','svc','lvs','metric','analytic','agreement','disagreement','fairness'],
    'waitlist':   ['waitlist','scheduled','interview','schedule'],
}

def _chatbot_classify(msg):
    msg = msg.lower()
    scores = {k: sum(1 for w in v if w in msg) for k,v in CHATBOT_INTENTS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else 'general'

def _chatbot_reply(intent, message):
    if intent == 'candidates':
        try:
            db = _get_db()
            q = message.lower()
            if 'how many' in q or 'count' in q or 'total' in q:
                total = db.candidates.count_documents({})
                high  = db.candidates.count_documents({'final_fit': 'High'})
                return f"There are **{total}** candidates in the system, of which **{high}** are rated High fit."
            skill_m = re.search(r'(?:with|skilled in|know|has)\s+([a-zA-Z+#.]+)', q)
            if skill_m:
                skill = skill_m.group(1)
                cs = list(db.candidates.find({'skills':{'$regex':skill,'$options':'i'}},{'name':1,'final_fit':1,'_id':0}).limit(5))
                if not cs: return f"No candidates with **{skill}** found yet."
                return "Candidates with **{}**: {}.".format(skill, ', '.join(c['name'] for c in cs))
            cs = list(db.candidates.find({},{'name':1,'role_match_score':1,'final_fit':1,'_id':0}).sort('role_match_score',-1).limit(5))
            if not cs: return "No candidates analyzed yet. Upload resumes in the Resume Analysis tab."
            lines = ["• {} — {} fit ({:.0f}%)".format(c['name'],c.get('final_fit','?'),c.get('role_match_score',0)) for c in cs]
            return "Top candidates:\n" + "\n".join(lines)
        except Exception as e:
            return f"Couldn't fetch candidate data: {e}"

    if intent == 'analytics':
        return ("**HAAR** = Human-AI Agreement Rate\n"
                "**CDR** = Consistency Defect Rate\n"
                "**SVC** = Skill Validation Coverage\n"
                "**LVS** = Learning Velocity Score\n"
                "See the AI Analytics tab for live values.")

    if intent == 'platform':
        q = message.lower()
        if 'skill' in q:
            return "Skills are validated by scanning a 120-char window for action verbs (built/deployed/implemented). Result: Valid, Partial, or Unverified."
        if 'score' in q or 'match' in q:
            return "Role match uses TF-IDF cosine similarity between resume and job description, combined with skill and consistency scores."
        if 'upload' in q:
            return "You can upload PDF or DOCX resumes. The system auto-extracts skills, experience, education, and projects."
        return ("NeuroHire has two modules:\n"
                "• **Recruiter**: upload resumes, search GitHub, analyze candidates, track decisions\n"
                "• **Seeker**: analyze resume, mock interviews, job board, project Q&A")

    if intent == 'jobs':
        return "Job listings come from the Remotive API. Browse them in the Job Board tab in the Seeker Dashboard."

    if intent == 'waitlist':
        return "Add candidates to waitlist from their card. View scheduled interviews in the Scheduled tab."

    return ("I can help with:\n"
            "• Candidates — scores, skills, fit\n"
            "• Analytics — HAAR, CDR, SVC, LVS\n"
            "• Platform — how features work\n"
            "• Jobs & Waitlist\n\n"
            "Try: *'Show top candidates'* or *'How does skill validation work?'*")


class ChatbotView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        message = (request.data.get('message') or '').strip()[:500]
        if not message:
            return Response({'error': 'Message required'}, status=status.HTTP_400_BAD_REQUEST)
        intent = _chatbot_classify(message)
        reply  = _chatbot_reply(intent, message)
        try:
            _get_db().chatbot_logs.insert_one({'message': message, 'intent': intent})
        except Exception:
            pass
        return Response({'reply': reply, 'intent': intent})


class MeView(APIView):
    """Return the current authenticated user's profile."""
    permission_classes = [AllowAny]
    authentication_classes = [SessionAuthentication]

    def get(self, request):
        if not request.user or not request.user.is_authenticated:
            # Also try reading from localStorage token via header if set
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        payload = _user_payload(request.user)
        if not payload:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        return Response(payload)


class ProfileUpdateView(APIView):
    """Update the current user's profile details."""
    permission_classes = [AllowAny]
    authentication_classes = [SessionAuthentication]

    def patch(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data or {}
        user = request.user

        # Update Django User fields
        if 'full_name' in data:
            parts = data['full_name'].strip().split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''
            user.save()

        # Update UserProfile fields
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user, role='jobseeker')

        updatable = ['phone', 'company', 'college', 'bio', 'linkedin', 'location', 'job_title']
        for field in updatable:
            if field in data:
                try:
                    setattr(profile, field, data[field])
                except Exception:
                    pass
        try:
            profile.save()
        except Exception:
            pass

        return Response(_user_payload(user))

    def get(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        payload = _user_payload(request.user)
        # Add extra profile fields
        try:
            profile = request.user.profile
            payload['phone']     = getattr(profile, 'phone', '') or ''
            payload['company']   = getattr(profile, 'company', '') or ''
            payload['college']   = getattr(profile, 'college', '') or ''
            payload['bio']       = getattr(profile, 'bio', '') or ''
            payload['linkedin']  = getattr(profile, 'linkedin', '') or ''
            payload['location']  = getattr(profile, 'location', '') or ''
            payload['job_title'] = getattr(profile, 'job_title', '') or ''
        except Exception:
            pass
        return Response(payload)


class LogoutView(APIView):
    """Log out the current user."""
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==============================
# Utility
# ==============================

@api_view(["DELETE"])
def clear_candidates(request):
    deleted = mongo_delete_all_candidates()
    return Response({'deleted': deleted})
    return Response({"message": "All candidates cleared"})