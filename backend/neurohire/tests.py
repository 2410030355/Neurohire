from django.test import TestCase

# Create your tests here.
"""
NeuroHire — Unit tests for core AI scoring functions.

Run with:
    python manage.py test neurohire

Covers the evaluation-critical functions referenced in the paper:
  - compute_consistency_score()   (§IV.A — cross-document consistency)
  - validate_skills_from_text()   (§IV.B — evidence-backed skill validation)
  - compute_role_match()          (§IV.E — role-specific suitability)
  - compute_final_fit()           (final classification thresholds)
  - mongo_insert_candidate dedup  (§III.B — unified candidate representation)
"""
from django.test import TestCase
from unittest.mock import patch, MagicMock

from neurohire.analysis_engine import (
    compute_consistency_score,
    validate_skills_from_text,
    compute_role_match,
    compute_final_fit,
    compute_resume_strength_score,
)


# ════════════════════════════════════════════════════════════════════════════
# Consistency Scoring (paper §IV.D.1) — exactly three rules, no floor
# ════════════════════════════════════════════════════════════════════════════

class ConsistencyScoreTests(TestCase):

    def test_clean_profile_scores_full_100(self):
        skills = ['python', 'sql', 'git', 'linux']
        self.assertEqual(compute_consistency_score(skills, experience_years=2.0), 100.0)

    def test_senior_skill_with_low_experience_is_penalised(self):
        """Rule 1: Kubernetes with < 1.5 years deducts 20."""
        skills = ['kubernetes', 'python', 'git']
        self.assertEqual(compute_consistency_score(skills, experience_years=0.5), 80.0)

    def test_too_many_skills_for_experience_is_penalised(self):
        """Rule 2: more than K_max = max(6, 4Y) skills deducts 12."""
        many_skills = [f'skill_{i}' for i in range(20)]
        self.assertEqual(compute_consistency_score(many_skills, experience_years=1.0), 88.0)

    def test_skill_limit_boundary(self):
        """Exactly K_max skills is allowed (rule uses >)."""
        self.assertEqual(compute_consistency_score([f's{i}' for i in range(8)], 2.0), 100.0)
        self.assertEqual(compute_consistency_score([f's{i}' for i in range(9)], 2.0), 88.0)

    def test_advanced_tool_without_foundation_is_penalised(self):
        """Rule 3: Kubernetes without a foundational skill deducts 15."""
        self.assertEqual(compute_consistency_score(['kubernetes'], experience_years=2.0), 85.0)

    def test_no_fourth_rule_for_experienced_few_skills(self):
        """The old '3+ years with < 4 skills' rule is not in the paper."""
        self.assertEqual(compute_consistency_score(['python', 'git'], experience_years=5.0), 100.0)

    def test_all_three_rules_stack_without_floor(self):
        """100 - 20 - 12 - 15 = 53: deductions add up, no lower bound applied."""
        skills = ['kubernetes', 'terraform', 'kafka'] + [f'x{i}' for i in range(5)]
        self.assertEqual(compute_consistency_score(skills, experience_years=0.2), 53.0)

    def test_unknown_experience_skips_experience_rules(self):
        from neurohire.scoring import compute_consistency
        r = compute_consistency(['kubernetes', 'python'] + [f'x{i}' for i in range(10)], None)
        self.assertEqual(r['score'], 100.0)
        self.assertEqual(len(r['rules_skipped']), 2)


# ════════════════════════════════════════════════════════════════════════════
# Skill validation (paper §IV.D.2)
# ════════════════════════════════════════════════════════════════════════════

class SkillValidationTests(TestCase):

    def test_skill_with_action_verb_nearby_is_valid(self):
        text = "i built a payment system using python and deployed it on aws"
        self.assertEqual(validate_skills_from_text(['python'], text)[0]['status'], 'Valid')

    def test_skill_mentioned_twice_without_verb_is_partial(self):
        text = "skills: react, javascript. familiar with react basics."
        self.assertEqual(validate_skills_from_text(['react'], text)[0]['status'], 'Partial')

    def test_skill_not_in_text_is_unverified(self):
        text = "experienced python developer"
        self.assertEqual(validate_skills_from_text(['kubernetes'], text)[0]['status'], 'Unverified')

    def test_skill_mentioned_once_with_no_verb_is_unverified(self):
        self.assertEqual(validate_skills_from_text(['docker'], "skills include docker")[0]['status'], 'Unverified')

    def test_multiple_skills_classified_independently(self):
        text = ("built a react app for the analytics team.\n"
                + "x" * 80 + "\nalso know terraform basics. terraform terraform.")
        statuses = {r['skill']: r['status'] for r in validate_skills_from_text(['react', 'terraform', 'rust'], text)}
        self.assertEqual(statuses, {'react': 'Valid', 'terraform': 'Partial', 'rust': 'Unverified'})

    def test_used_is_not_an_action_verb(self):
        """Only the paper's verb list counts ('used' is not in it)."""
        self.assertEqual(validate_skills_from_text(['docker'], "used docker")[0]['status'], 'Unverified')

    def test_java_mention_inside_javascript_is_not_evidence(self):
        r = validate_skills_from_text(['java'], "developed javascript widgets")[0]
        self.assertEqual(r['status'], 'Unverified')


# ════════════════════════════════════════════════════════════════════════════
# Semantic similarity (paper §IV.C)
# ════════════════════════════════════════════════════════════════════════════

class RoleMatchTests(TestCase):

    def test_empty_target_is_not_computable(self):
        """Nothing to match against: SS is None, not a made-up neutral 50."""
        self.assertIsNone(compute_role_match("some resume text", "", []))

    def test_relevant_resume_scores_higher_than_irrelevant(self):
        jd = "looking for a react frontend developer with typescript and redux experience"
        relevant = compute_role_match("experienced react developer skilled in typescript and redux state management",
                                      "Frontend Developer", [], jd)
        irrelevant = compute_role_match("java backend engineer with spring boot and oracle database experience",
                                        "Frontend Developer", [], jd)
        self.assertGreater(relevant, irrelevant)

    def test_score_is_within_valid_bounds(self):
        score = compute_role_match("python django developer", "Backend Developer", ['python', 'django'])
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_no_keyword_bonus(self):
        """SS is cosine only: listing skills cannot raise it."""
        a = compute_role_match("react developer", "react", [], "react")
        b = compute_role_match("react developer", "react", ['react', 'redux', 'jest'], "react")
        self.assertEqual(a, b)


# ════════════════════════════════════════════════════════════════════════════
# Final fit thresholds
# ════════════════════════════════════════════════════════════════════════════

class FinalFitTests(TestCase):

    def test_high_score_classified_as_high_fit(self):
        self.assertEqual(compute_final_fit(85), 'High')

    def test_medium_score_classified_as_medium_fit(self):
        self.assertEqual(compute_final_fit(55), 'Medium')

    def test_low_score_classified_as_low_fit(self):
        self.assertEqual(compute_final_fit(20), 'Low')

    def test_boundary_at_70_is_high(self):
        self.assertEqual(compute_final_fit(70), 'High')

    def test_boundary_at_40_is_medium(self):
        self.assertEqual(compute_final_fit(40), 'Medium')


class ResumeStrengthTests(TestCase):

    def test_resume_strength_caps_at_100(self):
        score = compute_resume_strength_score([f'skill_{i}' for i in range(50)], "PhD", experience_years=20)
        self.assertLessEqual(score, 100.0)

    def test_resume_strength_increases_with_education_level(self):
        self.assertGreater(compute_resume_strength_score(['python'], 'PhD', 2.0),
                           compute_resume_strength_score(['python'], None, 2.0))


# ════════════════════════════════════════════════════════════════════════════
# Paper formulas (§IV.E)
# ════════════════════════════════════════════════════════════════════════════

class PaperFormulaTests(TestCase):

    def test_analytical_score_is_mean_of_three_components(self):
        from neurohire.analysis_engine import compute_analytical_score
        self.assertAlmostEqual(compute_analytical_score(80, 60, 70), 70.0, places=2)

    def test_final_score_is_0_6_ss_plus_0_4_as(self):
        from neurohire.analysis_engine import compute_final_score
        self.assertAlmostEqual(compute_final_score(80, 60), 72.0, places=2)

    def test_full_pipeline_produces_consistent_final_fit(self):
        from neurohire.analysis_engine import compute_analytical_score, compute_final_score
        fs = compute_final_score(85.0, compute_analytical_score(90, 80, 75))
        self.assertEqual(compute_final_fit(fs), 'High')

    def test_low_ss_high_as_is_medium(self):
        from neurohire.analysis_engine import compute_analytical_score, compute_final_score
        fs = compute_final_score(30.0, compute_analytical_score(85, 80, 75))  # 0.6*30 + 0.4*80 = 50
        self.assertAlmostEqual(fs, 50.0, places=2)
        self.assertEqual(compute_final_fit(fs), 'Medium')


# ════════════════════════════════════════════════════════════════════════════
# Candidate Deduplication (paper §III.B — unified candidate representation)
# ════════════════════════════════════════════════════════════════════════════

class CandidateDeduplicationTests(TestCase):
    """
    Tests mongo_insert_candidate's merge-by-email logic using a mocked
    MongoDB collection — no real database connection required.
    """

    @patch('neurohire.mongo_client.candidates_collection')
    def test_new_email_creates_fresh_document(self, mock_collection):
        from neurohire.mongo_client import mongo_insert_candidate

        mock_col = MagicMock()
        mock_col.find_one.return_value = None  # no existing match
        mock_col.insert_one.return_value = MagicMock(inserted_id='abc123')
        mock_collection.return_value = mock_col

        result = mongo_insert_candidate({
            'name': 'Test User', 'email': 'test@example.com',
            'skills': ['python'], 'source': 'resume_upload',
        })

        mock_col.insert_one.assert_called_once()
        mock_col.update_one.assert_not_called()
        self.assertEqual(result, 'abc123')

    @patch('neurohire.mongo_client.candidates_collection')
    def test_existing_email_merges_instead_of_duplicating(self, mock_collection):
        from neurohire.mongo_client import mongo_insert_candidate
        from bson import ObjectId

        existing_id = ObjectId()
        mock_col = MagicMock()
        mock_col.find_one.return_value = {
            '_id': existing_id,
            'email': 'test@example.com',
            'skills': ['python', 'django'],
            'companies': ['CompanyA'],
            'source': 'github_search',
        }
        mock_collection.return_value = mock_col

        result = mongo_insert_candidate({
            'name': 'Test User', 'email': 'test@example.com',
            'skills': ['python', 'react'],  # overlapping + new skill
            'companies': ['CompanyB'],
            'source': 'resume_upload',
        })

        # Should UPDATE the existing doc, not insert a new one
        mock_col.insert_one.assert_not_called()
        mock_col.update_one.assert_called_once()
        self.assertEqual(result, str(existing_id))

        # Verify skills were merged (union), not overwritten
        call_args = mock_col.update_one.call_args
        update_data = call_args[0][1]['$set']
        self.assertIn('python', update_data['skills'])
        self.assertIn('django', update_data['skills'])
        self.assertIn('react', update_data['skills'])

# ════════════════════════════════════════════════════════════════════════════
# Security hardening (Task 0) — access control, CSRF origin check,
# no hardcoded credentials, uploaded résumés not retained on disk.
# ════════════════════════════════════════════════════════════════════════════

import json
import os
import re
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings

from neurohire.models import UserProfile

TRUSTED_ORIGIN = 'https://neurohire-bay.vercel.app'


@override_settings(CORS_ALLOWED_ORIGINS=[TRUSTED_ORIGIN])
class SecurityHardeningTests(TestCase):
    """Behaviour expected after Task 0. Uses a CSRF-enforcing client, like a browser."""

    def setUp(self):
        User = get_user_model()
        self.client = Client(enforce_csrf_checks=True)

        self.recruiter = User.objects.create_user('rec@company.com', 'rec@company.com', 'pw-12345678')
        UserProfile.objects.create(user=self.recruiter, role='recruiter')

        self.seeker = User.objects.create_user('seek@example.com', 'seek@example.com', 'pw-12345678')
        UserProfile.objects.create(user=self.seeker, role='jobseeker')

        self.admin = User.objects.create_user('admin@company.com', 'admin@company.com', 'pw-12345678',
                                              is_staff=True)
        UserProfile.objects.create(user=self.admin, role='recruiter')

    def _decision_payload(self):
        return {
            'candidate_name': 'Test Candidate',
            'ai_recommendation': 'hire',
            'recruiter_decision': 'hire',
            'role_match_score': 80,
        }

    # ── Candidate list (contains personal data) ─────────────────────────
    @patch('neurohire.views.mongo_all_candidates', return_value=[{'name': 'A'}])
    def test_candidate_list_requires_login(self, _mock):
        self.assertEqual(self.client.get('/api/candidates/').status_code, 403)

    @patch('neurohire.views.mongo_all_candidates', return_value=[{'name': 'A'}])
    def test_candidate_list_forbidden_for_jobseeker(self, _mock):
        self.client.force_login(self.seeker)
        self.assertEqual(self.client.get('/api/candidates/').status_code, 403)

    @patch('neurohire.views.mongo_all_candidates', return_value=[{'name': 'A'}])
    def test_candidate_list_allowed_for_recruiter(self, _mock):
        self.client.force_login(self.recruiter)
        resp = self.client.get('/api/candidates/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [{'name': 'A'}])

    @patch('neurohire.views.mongo_get_candidate', return_value={'name': 'A'})
    def test_candidate_detail_requires_recruiter(self, _mock):
        self.assertEqual(self.client.get('/api/candidates/abc/').status_code, 403)
        self.client.force_login(self.recruiter)
        self.assertEqual(self.client.get('/api/candidates/abc/').status_code, 200)

    # ── Destructive clear endpoint ──────────────────────────────────────
    # NOTE: the router's candidates/<pk>/ route is registered first and captures
    # "clear" as a pk, so DELETE /api/candidates/clear/ never reaches
    # clear_candidates (it returns 405). The view is tested directly so it stays
    # safe if the route is ever re-ordered.
    @patch('neurohire.views.mongo_delete_all_candidates', return_value=5)
    def test_clear_url_never_deletes_for_anonymous(self, mock_delete):
        resp = self.client.delete('/api/candidates/clear/')
        self.assertIn(resp.status_code, (403, 405))
        mock_delete.assert_not_called()

    def _call_clear_view(self, user, origin=TRUSTED_ORIGIN):
        from rest_framework.test import APIRequestFactory, force_authenticate
        from neurohire.views import clear_candidates
        request = APIRequestFactory().delete('/api/candidates/clear/', HTTP_ORIGIN=origin)
        if user is not None:
            force_authenticate(request, user=user)
        return clear_candidates(request)

    @patch('neurohire.views.mongo_delete_all_candidates', return_value=5)
    def test_clear_view_blocked_for_anonymous(self, mock_delete):
        self.assertEqual(self._call_clear_view(None).status_code, 403)
        mock_delete.assert_not_called()

    @patch('neurohire.views.mongo_delete_all_candidates', return_value=5)
    def test_clear_view_blocked_for_non_staff_recruiter(self, mock_delete):
        self.assertEqual(self._call_clear_view(self.recruiter).status_code, 403)
        mock_delete.assert_not_called()

    @patch('neurohire.views.mongo_delete_all_candidates', return_value=5)
    def test_clear_view_allowed_for_staff(self, mock_delete):
        resp = self._call_clear_view(self.admin)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, {'deleted': 5})
        mock_delete.assert_called_once()

    # ── Decision log (drives the adaptive weights) ──────────────────────
    @patch('neurohire.views.update_weights')
    def test_decision_log_post_blocked_for_anonymous(self, mock_update):
        resp = self.client.post('/api/ai-decision-logs/', self._decision_payload(),
                                content_type='application/json', HTTP_ORIGIN=TRUSTED_ORIGIN)
        self.assertEqual(resp.status_code, 403)
        mock_update.assert_not_called()

    @patch('neurohire.views.update_weights')
    def test_decision_log_post_blocked_for_jobseeker(self, mock_update):
        self.client.force_login(self.seeker)
        resp = self.client.post('/api/ai-decision-logs/', self._decision_payload(),
                                content_type='application/json', HTTP_ORIGIN=TRUSTED_ORIGIN)
        self.assertEqual(resp.status_code, 403)
        mock_update.assert_not_called()

    def test_decision_log_list_requires_recruiter(self):
        self.assertEqual(self.client.get('/api/ai-decision-logs/').status_code, 403)
        self.client.force_login(self.recruiter)
        self.assertEqual(self.client.get('/api/ai-decision-logs/').status_code, 200)

    @patch('neurohire.views.update_weights')
    def test_decision_log_post_allowed_for_recruiter_from_trusted_origin(self, mock_update):
        """The real frontend sends no CSRF token (it can't read a cross-site cookie);
        a trusted Origin must be enough, otherwise the dashboard breaks."""
        self.client.force_login(self.recruiter)
        resp = self.client.post('/api/ai-decision-logs/', self._decision_payload(),
                                content_type='application/json', HTTP_ORIGIN=TRUSTED_ORIGIN)
        self.assertEqual(resp.status_code, 201, resp.content)
        mock_update.assert_called_once()

    @patch('neurohire.views.update_weights')
    def test_decision_log_post_rejected_from_untrusted_origin(self, mock_update):
        """Cross-site request forgery: logged-in recruiter's browser, attacker's page."""
        self.client.force_login(self.recruiter)
        resp = self.client.post('/api/ai-decision-logs/', self._decision_payload(),
                                content_type='application/json', HTTP_ORIGIN='https://evil.example')
        self.assertEqual(resp.status_code, 403)
        mock_update.assert_not_called()

    @patch('neurohire.views.update_weights')
    def test_decision_log_post_rejected_with_null_origin(self, mock_update):
        self.client.force_login(self.recruiter)
        resp = self.client.post('/api/ai-decision-logs/', self._decision_payload(),
                                content_type='application/json', HTTP_ORIGIN='null')
        self.assertEqual(resp.status_code, 403)
        mock_update.assert_not_called()

    @patch('neurohire.views.update_weights')
    def test_decision_log_post_rejected_from_untrusted_referer_without_origin(self, mock_update):
        self.client.force_login(self.recruiter)
        resp = self.client.post('/api/ai-decision-logs/', self._decision_payload(),
                                content_type='application/json',
                                HTTP_REFERER='https://evil.example/page')
        self.assertEqual(resp.status_code, 403)
        mock_update.assert_not_called()

    @patch('neurohire.views.update_weights')
    def test_decision_log_rejects_form_encoded_body(self, mock_update):
        """Only JSON is accepted, so a plain HTML form (no CORS preflight) can't post."""
        self.client.force_login(self.recruiter)
        resp = self.client.post('/api/ai-decision-logs/', self._decision_payload(),
                                HTTP_ORIGIN=TRUSTED_ORIGIN)  # multipart form
        self.assertEqual(resp.status_code, 415)
        mock_update.assert_not_called()

    @override_settings(CORS_ALLOWED_ORIGINS=[TRUSTED_ORIGIN],
                       CORS_ORIGIN_WHITELIST=['http://localhost:5173'])
    @patch('neurohire.views.update_weights')
    def test_origin_trust_matches_what_cors_allows(self, mock_update):
        """CORS ignores CORS_ORIGIN_WHITELIST when CORS_ALLOWED_ORIGINS is set,
        so the CSRF origin check must ignore it too."""
        self.client.force_login(self.recruiter)
        resp = self.client.post('/api/ai-decision-logs/', self._decision_payload(),
                                content_type='application/json', HTTP_ORIGIN='http://localhost:5173')
        self.assertEqual(resp.status_code, 403)
        mock_update.assert_not_called()

    # ── No hardcoded credentials ────────────────────────────────────────
    def test_settings_contain_no_credentialed_connection_string(self):
        source = (Path(settings.BASE_DIR) / 'backend' / 'settings.py').read_text(encoding='utf-8')
        self.assertIsNone(re.search(r'mongodb(\+srv)?://[^\s/\'"]+:[^\s@\'"]+@', source),
                          'settings.py must not contain a MongoDB URI with a username:password')

    # ── Uploaded résumés are not retained on disk ───────────────────────
    def _upload_dir_files(self):
        from neurohire.views import UPLOAD_DIR
        return set(os.listdir(UPLOAD_DIR))

    @patch('neurohire.views.mongo_insert_candidate', return_value='id1')
    @patch('neurohire.views.analyze_resume', return_value={'name': 'A', 'skills': []})
    def test_recruiter_upload_file_deleted_after_analysis(self, _an, _ins):
        self.client.force_login(self.recruiter)
        before = self._upload_dir_files()
        f = SimpleUploadedFile('cv.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        resp = self.client.post('/api/upload-resume/', {'resume': f, 'target_role': 'Dev'})
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(self._upload_dir_files(), before)

    @patch('neurohire.views.analyze_resume', side_effect=Exception('boom'))
    def test_recruiter_upload_file_deleted_when_analysis_fails(self, _an):
        self.client.force_login(self.recruiter)
        before = self._upload_dir_files()
        f = SimpleUploadedFile('cv.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        resp = self.client.post('/api/upload-resume/', {'resume': f, 'target_role': 'Dev'})
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(self._upload_dir_files(), before)

    @patch('neurohire.views.analyze_resume', return_value={'name': 'A', 'skills': []})
    def test_seeker_upload_file_deleted_after_analysis(self, _an):
        self.client.force_login(self.seeker)
        before = self._upload_dir_files()
        f = SimpleUploadedFile('cv.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        resp = self.client.post('/api/seeker-resume/', {'resume': f, 'target_role': 'Dev'})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(self._upload_dir_files(), before)


@override_settings(CORS_ALLOWED_ORIGINS=[TRUSTED_ORIGIN])
class CorsPreflightTests(TestCase):
    """The CSRF defence relies on browsers refusing to send a JSON/DELETE request
    when the CORS preflight is not approved for the requesting origin."""

    def _preflight(self, origin, method='POST'):
        return Client().options('/api/ai-decision-logs/', HTTP_ORIGIN=origin,
                                HTTP_ACCESS_CONTROL_REQUEST_METHOD=method,
                                HTTP_ACCESS_CONTROL_REQUEST_HEADERS='content-type')

    def test_preflight_denied_for_untrusted_origin(self):
        resp = self._preflight('https://evil.example')
        self.assertNotIn('access-control-allow-origin', {k.lower() for k in resp.headers})

    def test_preflight_allowed_for_frontend_origin(self):
        resp = self._preflight(TRUSTED_ORIGIN)
        self.assertEqual(resp.headers.get('Access-Control-Allow-Origin'), TRUSTED_ORIGIN)
        self.assertEqual(resp.headers.get('Access-Control-Allow-Credentials'), 'true')



# ════════════════════════════════════════════════════════════════════════════
# Task 0 (part 2): recruiter allowlist, Google sign-in role, upload limits,
# quota-spending endpoints
# ════════════════════════════════════════════════════════════════════════════

@override_settings(ALLOWED_RECRUITER_EMAILS=['approved@gmail.com'],
                   ALLOWED_RECRUITER_DOMAINS=['company.com'],
                   CORS_ALLOWED_ORIGINS=[TRUSTED_ORIGIN])
class RecruiterAllowlistTests(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.User = get_user_model()

    def _register(self, email, role='recruiter'):
        return self.client.post('/api/auth/register/', data=json.dumps({
            'email': email, 'password': 'pw-12345678', 'full_name': 'X Y', 'role': role,
        }), content_type='application/json')

    def _login(self, email, role=None):
        body = {'email': email, 'password': 'pw-12345678'}
        if role:
            body['role'] = role
        return self.client.post('/api/auth/login/', data=json.dumps(body), content_type='application/json')

    def test_helper_matches_email_and_domain_case_insensitively(self):
        from neurohire.access import is_allowed_recruiter_email
        self.assertTrue(is_allowed_recruiter_email('Approved@Gmail.com'))
        self.assertTrue(is_allowed_recruiter_email('anyone@COMPANY.com'))
        self.assertFalse(is_allowed_recruiter_email('other@gmail.com'))
        self.assertFalse(is_allowed_recruiter_email('x@notcompany.com'))
        self.assertFalse(is_allowed_recruiter_email(''))
        self.assertFalse(is_allowed_recruiter_email(None))

    def test_register_recruiter_with_allowlisted_gmail(self):
        self.assertEqual(self._register('approved@gmail.com').status_code, 201)
        self.assertEqual(self.User.objects.get(username='approved@gmail.com').profile.role, 'recruiter')

    def test_register_recruiter_with_unapproved_gmail_is_refused(self):
        resp = self._register('random@gmail.com')
        self.assertEqual(resp.status_code, 403)
        self.assertNotIn('approved@gmail.com', resp.content.decode())  # allowlist not leaked
        self.assertFalse(self.User.objects.filter(username='random@gmail.com').exists())

    def test_jobseeker_signup_unaffected(self):
        self.assertEqual(self._register('random@gmail.com', role='jobseeker').status_code, 201)

    def test_recruiter_login_upgrades_approved_seeker_account(self):
        u = self.User.objects.create_user('approved@gmail.com', 'approved@gmail.com', 'pw-12345678')
        UserProfile.objects.create(user=u, role='jobseeker')
        resp = self._login('approved@gmail.com', role='recruiter')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()['role'], 'recruiter')

    def test_recruiter_login_refused_for_unapproved_account(self):
        u = self.User.objects.create_user('random@gmail.com', 'random@gmail.com', 'pw-12345678')
        UserProfile.objects.create(user=u, role='jobseeker')
        self.assertEqual(self._login('random@gmail.com', role='recruiter').status_code, 403)
        u.profile.refresh_from_db()
        self.assertEqual(u.profile.role, 'jobseeker')

    def test_plain_login_does_not_change_role(self):
        u = self.User.objects.create_user('approved@gmail.com', 'approved@gmail.com', 'pw-12345678')
        UserProfile.objects.create(user=u, role='recruiter')
        resp = self._login('approved@gmail.com')
        self.assertEqual(resp.json()['role'], 'recruiter')

    @patch('neurohire.views.mongo_all_candidates', return_value=[])
    def test_removing_email_from_allowlist_revokes_access(self, _m):
        u = self.User.objects.create_user('approved@gmail.com', 'approved@gmail.com', 'pw-12345678')
        UserProfile.objects.create(user=u, role='recruiter')
        self.client.force_login(u)
        self.assertEqual(self.client.get('/api/candidates/').status_code, 200)
        with override_settings(ALLOWED_RECRUITER_EMAILS=[]):
            self.assertEqual(self.client.get('/api/candidates/').status_code, 403)


@override_settings(ALLOWED_RECRUITER_EMAILS=['approved@gmail.com'], ALLOWED_RECRUITER_DOMAINS=[])
class GoogleSignInRoleTests(TestCase):
    """neurohire.pipeline.save_user_profile with a fake social-auth backend."""

    def _run(self, email, session_role, existing_role=None):
        from neurohire.pipeline import save_user_profile, set_redirect_url
        from django.contrib.sessions.backends.db import SessionStore
        u = get_user_model().objects.create_user(email, email, 'pw-12345678')
        if existing_role:
            UserProfile.objects.create(user=u, role=existing_role)
        session = SessionStore()
        if session_role:
            session['role'] = session_role
        backend = MagicMock()
        backend.strategy.session_get.side_effect = lambda k, d=None: session.get(k, d)
        backend.strategy.session_set.side_effect = lambda k, v: session.__setitem__(k, v)
        request = MagicMock()
        request.GET = {}
        request.session = session
        save_user_profile(backend, u, {'name': 'Some One', 'email': email}, request)
        set_redirect_url(backend, u, {}, request)
        u.profile.refresh_from_db()
        return u.profile.role, session.get('next', '')

    def test_approved_gmail_becomes_recruiter(self):
        role, nxt = self._run('approved@gmail.com', 'recruiter')
        self.assertEqual(role, 'recruiter')
        self.assertTrue(nxt.endswith('/RecruiterDashboard'))

    def test_unapproved_gmail_gets_seeker_and_error_redirect(self):
        role, nxt = self._run('random@gmail.com', 'recruiter')
        self.assertEqual(role, 'jobseeker')
        self.assertIn('/RecruiterAuth?error=not_approved', nxt)

    def test_missing_role_no_longer_demotes_existing_recruiter(self):
        role, _ = self._run('approved@gmail.com', None, existing_role='recruiter')
        self.assertEqual(role, 'recruiter')

    def test_seeker_button_creates_seeker(self):
        role, nxt = self._run('random@gmail.com', 'jobseeker')
        self.assertEqual(role, 'jobseeker')
        self.assertTrue(nxt.endswith('/SeekerDashboard'))

    def test_role_param_is_kept_through_oauth_session(self):
        from django.conf import settings
        self.assertIn('role', settings.SOCIAL_AUTH_FIELDS_STORED_IN_SESSION)


@override_settings(CORS_ALLOWED_ORIGINS=[TRUSTED_ORIGIN], MAX_UPLOAD_MB=1)
class UploadAndQuotaEndpointTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.client = Client(enforce_csrf_checks=True)
        self.recruiter = User.objects.create_user('rec@company.com', 'rec@company.com', 'pw-12345678')
        UserProfile.objects.create(user=self.recruiter, role='recruiter')
        self.seeker = User.objects.create_user('seek@example.com', 'seek@example.com', 'pw-12345678')
        UserProfile.objects.create(user=self.seeker, role='jobseeker')

    def _upload(self, url, name, content):
        return self.client.post(url, {'resume': SimpleUploadedFile(name, content), 'target_role': 'Dev'},
                                HTTP_ORIGIN=TRUSTED_ORIGIN)

    @patch('neurohire.views.analyze_resume')
    def test_recruiter_upload_requires_recruiter(self, an):
        self.assertEqual(self._upload('/api/upload-resume/', 'cv.pdf', b'%PDF').status_code, 403)
        self.client.force_login(self.seeker)
        self.assertEqual(self._upload('/api/upload-resume/', 'cv.pdf', b'%PDF').status_code, 403)
        an.assert_not_called()

    @patch('neurohire.views.analyze_resume')
    def test_seeker_upload_requires_login(self, an):
        self.assertEqual(self._upload('/api/seeker-resume/', 'cv.pdf', b'%PDF').status_code, 403)
        an.assert_not_called()

    @patch('neurohire.views.analyze_resume')
    def test_upload_from_untrusted_origin_rejected(self, an):
        self.client.force_login(self.recruiter)
        resp = self.client.post('/api/upload-resume/', {'resume': SimpleUploadedFile('cv.pdf', b'%PDF')},
                                HTTP_ORIGIN='https://evil.example')
        self.assertEqual(resp.status_code, 403)
        an.assert_not_called()

    @patch('neurohire.views.analyze_resume')
    def test_wrong_extension_rejected(self, an):
        self.client.force_login(self.recruiter)
        for name in ('cv.exe', 'cv.doc', 'cv', 'cv.pdf.html'):
            resp = self._upload('/api/upload-resume/', name, b'data')
            self.assertEqual(resp.status_code, 400, name)
        an.assert_not_called()

    @patch('neurohire.views.analyze_resume')
    def test_oversized_and_empty_files_rejected(self, an):
        self.client.force_login(self.seeker)
        self.assertEqual(self._upload('/api/seeker-resume/', 'cv.pdf', b'x' * (1024 * 1024 + 1)).status_code, 400)
        self.assertEqual(self._upload('/api/seeker-resume/', 'cv.docx', b'').status_code, 400)
        an.assert_not_called()

    @patch('neurohire.views.mongo_insert_candidate', return_value='id1')
    @patch('neurohire.views.analyze_resume', return_value={'name': 'A', 'skills': []})
    def test_client_filename_never_used_as_path(self, an, ins):
        self.client.force_login(self.recruiter)
        resp = self._upload('/api/upload-resume/', '../../etc/evil.pdf', b'%PDF')
        self.assertEqual(resp.status_code, 201, resp.content)
        from neurohire.views import UPLOAD_DIR
        used_path = an.call_args[0][0]
        self.assertEqual(os.path.dirname(used_path), UPLOAD_DIR)
        self.assertNotIn('evil', used_path)
        self.assertNotIn('resume_url', ins.call_args[0][0])

    @patch('neurohire.views.github_search_service')
    def test_talent_search_is_recruiter_only(self, gh):
        body = json.dumps({'search_type': 'portal', 'role': 'frontend developer'})
        resp = self.client.post('/api/talent-search/', body, content_type='application/json',
                                HTTP_ORIGIN=TRUSTED_ORIGIN)
        self.assertEqual(resp.status_code, 403)
        self.client.force_login(self.recruiter)
        resp = self.client.post('/api/talent-search/', body, content_type='application/json',
                                HTTP_ORIGIN=TRUSTED_ORIGIN)
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_waitlist_recruiter_only_and_interviews_need_login(self):
        self.assertEqual(self.client.get('/api/waitlist/').status_code, 403)
        self.assertEqual(self.client.get('/api/interviews/').status_code, 403)
        self.client.force_login(self.seeker)
        self.assertEqual(self.client.get('/api/waitlist/').status_code, 403)
        self.assertEqual(self.client.get('/api/interviews/').status_code, 200)
        self.client.force_login(self.recruiter)
        self.assertEqual(self.client.get('/api/waitlist/').status_code, 200)

    def test_jobs_public_read_recruiter_write(self):
        self.assertEqual(self.client.get('/api/jobs/').status_code, 200)
        resp = self.client.post('/api/jobs/', '{}', content_type='application/json', HTTP_ORIGIN=TRUSTED_ORIGIN)
        self.assertEqual(resp.status_code, 403)

    def test_rate_limiting_is_configured(self):
        from django.conf import settings
        rf = settings.REST_FRAMEWORK
        self.assertIn('rest_framework.throttling.AnonRateThrottle', rf['DEFAULT_THROTTLE_CLASSES'])
        self.assertIn('anon', rf['DEFAULT_THROTTLE_RATES'])
