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
        read_only_fields = ("weight_update", "is_agreement", "created_at")

    def to_internal_value(self, data):
        # The frontend sends MongoDB / search ids in 'candidate'. Only a real
        # SQL Candidate pk belongs in the FK; anything else is a reference.
        data = data.copy() if hasattr(data, 'copy') else dict(data)
        cand = data.get('candidate')
        if cand not in (None, '') and not str(cand).isdigit():
            data.setdefault('candidate_ref', str(cand)[:64])
            data['candidate'] = None
        return super().to_internal_value(data)

    def validate(self, attrs):
        ai = attrs.get('ai_recommendation', getattr(self.instance, 'ai_recommendation', None))
        rec = attrs.get('recruiter_decision', getattr(self.instance, 'recruiter_decision', None))
        attrs['is_agreement'] = bool(ai and rec and ai == rec)
        return attrs


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