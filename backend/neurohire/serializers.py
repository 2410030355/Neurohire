from rest_framework import serializers
from .models import (
    Candidate,
    WaitlistEntry,
    AIDecisionLog,
    Interview,
    JobPosting,
    MockInterview,
)


class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = "__all__"


class WaitlistEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitlistEntry
        fields = "__all__"


class AIDecisionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIDecisionLog
        fields = "__all__"


class InterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interview
        fields = "__all__"


class JobPostingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosting
        fields = "__all__"


class MockInterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = MockInterview
        fields = "__all__"