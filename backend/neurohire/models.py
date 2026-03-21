from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


# ===============================
# 🔹 ENUM CHOICES
# ===============================

PRIORITY_CHOICES = [
    ("low", "Low"),
    ("medium", "Medium"),
    ("high", "High"),
]

AI_RECOMMENDATION_CHOICES = [
    ("hire", "Hire"),
    ("waitlist", "Waitlist"),
    ("reject", "Reject"),
]

STATUS_CHOICES = [
    ("new", "New"),
    ("analyzed", "Analyzed"),
    ("scheduled", "Scheduled"),
    ("waitlisted", "Waitlisted"),
    ("rejected", "Rejected"),
    ("hired", "Hired"),
]

LEARNING_VELOCITY_CHOICES = [
    ("Low", "Low"),
    ("Medium", "Medium"),
    ("High", "High"),
]

FIT_CHOICES = [
    ("Low", "Low"),
    ("Medium", "Medium"),
    ("High", "High"),
]

INTERVIEW_STATUS_CHOICES = [
    ("scheduled", "Scheduled"),
    ("completed", "Completed"),
    ("cancelled", "Cancelled"),
    ("no_show", "No Show"),
]

JOB_TYPE_CHOICES = [
    ("full_time", "Full Time"),
    ("part_time", "Part Time"),
    ("internship", "Internship"),
    ("contract", "Contract"),
]

JOB_STATUS_CHOICES = [
    ("active", "Active"),
    ("closed", "Closed"),
    ("draft", "Draft"),
]

MOCK_STATUS_CHOICES = [
    ("in_progress", "In Progress"),
    ("completed", "Completed"),
]

ROLE_CHOICES = [
    ("recruiter", "Recruiter"),
    ("jobseeker", "Job Seeker"),
]


# ===============================
# 👤 USER PROFILE (Role + Auth)
# ===============================

class UserProfile(models.Model):
    """
    Extends Django's built-in User with role information.
    One-to-one with the default User model.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="jobseeker",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} ({self.role})"

    @property
    def is_recruiter(self):
        return self.role == "recruiter"

    @property
    def is_jobseeker(self):
        return self.role == "jobseeker"


# ===============================
# 🧠 CANDIDATE (CORE MODEL)
# ===============================

class Candidate(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    resume_url = models.URLField(blank=True, null=True)

    source = models.CharField(
        max_length=50,
        choices=[
            ("resume_upload", "Resume Upload"),
            ("github_search", "GitHub Search"),
            ("job_portal_search", "Job Portal Search"),
        ],
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="new",
    )

    target_role = models.CharField(max_length=255, blank=True, null=True)

    # ===== AI SCORES =====
    consistency_score = models.FloatField(blank=True, null=True)
    skill_validation_score = models.FloatField(blank=True, null=True)
    learning_velocity = models.CharField(
        max_length=10,
        choices=LEARNING_VELOCITY_CHOICES,
        blank=True,
        null=True,
    )
    career_trajectory = models.TextField(blank=True, null=True)
    role_match_score = models.FloatField(blank=True, null=True)
    final_fit = models.CharField(
        max_length=10,
        choices=FIT_CHOICES,
        blank=True,
        null=True,
    )
    explainability = models.TextField(blank=True, null=True)

    # ===== PROFILE =====
    skills = models.JSONField(default=list, blank=True)
    experience_years = models.FloatField(blank=True, null=True)
    education = models.TextField(blank=True, null=True)

    github_url = models.URLField(blank=True, null=True)
    repo_score = models.FloatField(blank=True, null=True)
    profile_summary = models.TextField(blank=True, null=True)

    # ===== RESUME IMPROVEMENT =====
    resume_strength_score = models.FloatField(blank=True, null=True)
    improvement_suggestions = models.JSONField(default=list, blank=True)
    missing_skills = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ===============================
# 📋 WAITLIST
# ===============================

class WaitlistEntry(models.Model):
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name="waitlist_entries",
        null=True,
        blank=True,
    )
    candidate_name = models.CharField(max_length=255)
    role = models.CharField(max_length=255, blank=True, null=True)
    reason = models.TextField(blank=True, null=True)

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="medium",
    )

    match_score = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Waitlist - {self.candidate_name}"


# ===============================
# 🤖 AI DECISION LOG
# ===============================

class AIDecisionLog(models.Model):
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name="ai_logs",
        null=True,
        blank=True,
    )
    candidate_name = models.CharField(max_length=255)

    ai_recommendation = models.CharField(
        max_length=10,
        choices=AI_RECOMMENDATION_CHOICES,
    )
    recruiter_decision = models.CharField(
        max_length=10,
        choices=AI_RECOMMENDATION_CHOICES,
    )

    ai_confidence = models.FloatField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    is_agreement = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AI Log - {self.candidate_name}"


# ===============================
# 📅 INTERVIEW
# ===============================

class Interview(models.Model):
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name="interviews",
        null=True,
        blank=True,
    )
    candidate_name = models.CharField(max_length=255)
    role = models.CharField(max_length=255, blank=True, null=True)

    scheduled_date = models.DateTimeField()
    interview_link = models.URLField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=INTERVIEW_STATUS_CHOICES,
        default="scheduled",
    )

    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Interview - {self.candidate_name}"


# ===============================
# 💼 JOB POSTING
# ===============================

class JobPosting(models.Model):
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    requirements = models.JSONField(default=list, blank=True)
    skills_required = models.JSONField(default=list, blank=True)

    experience_range = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)

    job_type = models.CharField(
        max_length=20,
        choices=JOB_TYPE_CHOICES,
        default="full_time",
    )

    salary_range = models.CharField(max_length=100, blank=True, null=True)
    apply_url = models.URLField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=JOB_STATUS_CHOICES,
        default="active",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# ===============================
# 🎤 MOCK INTERVIEW
# ===============================

class MockInterview(models.Model):
    role = models.CharField(max_length=255)

    questions = models.JSONField(default=list, blank=True)

    overall_confidence = models.FloatField(blank=True, null=True)
    overall_clarity = models.FloatField(blank=True, null=True)
    total_filler_words = models.IntegerField(blank=True, null=True)
    avg_speaking_pace = models.CharField(max_length=50, blank=True, null=True)

    improvements = models.JSONField(default=list, blank=True)

    status = models.CharField(
        max_length=20,
        choices=MOCK_STATUS_CHOICES,
        default="in_progress",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Mock Interview - {self.role}"