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
    compute_skill_validation_score,
    compute_resume_strength_score,
)


# ════════════════════════════════════════════════════════════════════════════
# Consistency Scoring (paper §IV.A)
# ════════════════════════════════════════════════════════════════════════════

class ConsistencyScoreTests(TestCase):

    def test_clean_profile_scores_full_100(self):
        """A profile with no contradictions should score 100."""
        skills = ['python', 'sql', 'git', 'linux']
        score = compute_consistency_score(skills, experience_years=2.0)
        self.assertEqual(score, 100.0)

    def test_senior_skill_with_low_experience_is_penalised(self):
        """Claiming Kubernetes with under 1.5yr experience should deduct 20 points."""
        skills = ['kubernetes', 'python', 'git']
        score = compute_consistency_score(skills, experience_years=0.5)
        self.assertEqual(score, 80.0)

    def test_too_many_skills_for_experience_is_penalised(self):
        """Excessive skill count relative to experience should deduct 12 points."""
        many_skills = [f'skill_{i}' for i in range(20)]
        score = compute_consistency_score(many_skills, experience_years=1.0)
        self.assertLessEqual(score, 88.0)

    def test_advanced_tool_without_foundation_is_penalised(self):
        """Kubernetes without any foundational skill (python/git/sql/etc.) deducts 15."""
        skills = ['kubernetes']
        score = compute_consistency_score(skills, experience_years=2.0)
        self.assertEqual(score, 85.0)

    def test_high_experience_few_skills_is_penalised(self):
        """3+ years experience but under 4 skills detected deducts 18 points."""
        skills = ['python', 'git']
        score = compute_consistency_score(skills, experience_years=5.0)
        self.assertEqual(score, 82.0)

    def test_score_never_drops_below_floor_of_30(self):
        """Multiple stacked violations should still floor at 30, never negative."""
        skills = ['kubernetes', 'terraform', 'kafka']  # senior + advanced-without-foundation
        score = compute_consistency_score(skills, experience_years=0.2)
        self.assertGreaterEqual(score, 30.0)


# ════════════════════════════════════════════════════════════════════════════
# Evidence-Backed Skill Validation (paper §IV.B)
# ════════════════════════════════════════════════════════════════════════════

class SkillValidationTests(TestCase):

    def test_skill_with_action_verb_nearby_is_valid(self):
        """Skill mentioned near 'built'/'developed' etc. should be marked Valid."""
        text = "i built a payment system using python and deployed it on aws"
        result = validate_skills_from_text(['python'], text)
        self.assertEqual(result[0]['status'], 'Valid')

    def test_skill_mentioned_twice_without_verb_is_partial(self):
        """Skill appearing 2+ times with no nearby action verb should be Partial."""
        text = "skills: react, javascript. familiar with react basics."
        result = validate_skills_from_text(['react'], text)
        self.assertEqual(result[0]['status'], 'Partial')

    def test_skill_not_in_text_is_unverified(self):
        """A skill that never appears in the resume text should be Unverified."""
        text = "experienced python developer"
        result = validate_skills_from_text(['kubernetes'], text)
        self.assertEqual(result[0]['status'], 'Unverified')

    def test_skill_mentioned_once_with_no_verb_is_unverified(self):
        """Skill listed exactly once with zero evidence should be Unverified, not Partial."""
        text = "skills include docker"
        result = validate_skills_from_text(['docker'], text)
        self.assertEqual(result[0]['status'], 'Unverified')

    def test_multiple_skills_classified_independently(self):
        """Each skill in the list should get its own independent classification."""
        text = "built a react app, also know terraform basics. terraform terraform."
        result = validate_skills_from_text(['react', 'terraform', 'rust'], text)
        statuses = {r['skill']: r['status'] for r in result}
        self.assertEqual(statuses['react'], 'Valid')
        self.assertEqual(statuses['terraform'], 'Partial')
        self.assertEqual(statuses['rust'], 'Unverified')


# ════════════════════════════════════════════════════════════════════════════
# Role Match Scoring (paper §IV.E)
# ════════════════════════════════════════════════════════════════════════════

class RoleMatchTests(TestCase):

    def test_empty_role_returns_neutral_score(self):
        """No target role or JD provided should return the neutral default."""
        score = compute_role_match("some resume text", "", [])
        self.assertEqual(score, 50.0)

    def test_relevant_resume_scores_higher_than_irrelevant(self):
        """A resume closely matching the JD should score higher than an unrelated one."""
        jd = "looking for a react frontend developer with typescript and redux experience"
        relevant_resume   = "experienced react developer skilled in typescript and redux state management"
        irrelevant_resume = "java backend engineer with spring boot and oracle database experience"

        relevant_score   = compute_role_match(relevant_resume,   "Frontend Developer", ['react', 'typescript', 'redux'], jd)
        irrelevant_score = compute_role_match(irrelevant_resume, "Frontend Developer", ['java', 'spring boot'], jd)

        self.assertGreater(relevant_score, irrelevant_score)

    def test_score_is_within_valid_bounds(self):
        """Role match score should always be between 0 and 100."""
        score = compute_role_match("python django developer", "Backend Developer", ['python', 'django'])
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


# ════════════════════════════════════════════════════════════════════════════
# Final Fit Classification
# ════════════════════════════════════════════════════════════════════════════

class FinalFitTests(TestCase):

    def test_high_score_classified_as_high_fit(self):
        self.assertEqual(compute_final_fit(85), 'High')

    def test_medium_score_classified_as_medium_fit(self):
        self.assertEqual(compute_final_fit(55), 'Medium')  # now uses final_score not role_score

    def test_low_score_classified_as_low_fit(self):
        self.assertEqual(compute_final_fit(20), 'Low')

    def test_boundary_at_70_is_high(self):
        self.assertEqual(compute_final_fit(70), 'High')

    def test_boundary_at_40_is_medium(self):
        self.assertEqual(compute_final_fit(40), 'Medium')  # paper threshold: Medium >= 40


# ════════════════════════════════════════════════════════════════════════════
# Skill Validation & Resume Strength Scores
# ════════════════════════════════════════════════════════════════════════════

class ScoringFunctionTests(TestCase):

    def test_more_skills_increases_validation_score(self):
        few_skills  = compute_skill_validation_score(['python'], 'Medium')
        many_skills = compute_skill_validation_score(['python', 'django', 'sql', 'docker', 'aws'], 'Medium')
        self.assertGreater(many_skills, few_skills)

    def test_high_velocity_increases_validation_score(self):
        low  = compute_skill_validation_score(['python', 'sql'], 'Low')
        high = compute_skill_validation_score(['python', 'sql'], 'High')
        self.assertGreater(high, low)

    def test_resume_strength_caps_at_100(self):
        many_skills = [f'skill_{i}' for i in range(50)]
        score = compute_resume_strength_score(many_skills, "PhD", experience_years=20)
        self.assertLessEqual(score, 100.0)

    def test_resume_strength_increases_with_education_level(self):
        no_edu  = compute_resume_strength_score(['python'], None, 2.0)
        phd_edu = compute_resume_strength_score(['python'], 'PhD', 2.0)
        self.assertGreater(phd_edu, no_edu)


# ════════════════════════════════════════════════════════════════════════════
# Paper Formula Functions (§IV.F, §IV.G)
# ════════════════════════════════════════════════════════════════════════════

class PaperFormulaTests(TestCase):

    def test_analytical_score_is_mean_of_three_components(self):
        """AS = (CS + VS + LV) / 3 — must equal exact arithmetic mean."""
        from neurohire.analysis_engine import compute_analytical_score
        score = compute_analytical_score(80, 60, 70)
        self.assertAlmostEqual(score, 70.0, places=1)

    def test_final_score_is_weighted_sum(self):
        """FS = 0.5 * SS + 0.5 * AS with default weights."""
        from neurohire.analysis_engine import compute_final_score
        score = compute_final_score(80, 60)
        self.assertAlmostEqual(score, 70.0, places=1)

    def test_lv_score_increases_with_more_skills_per_year(self):
        """Higher skill count relative to experience = higher LV score."""
        from neurohire.analysis_engine import compute_learning_velocity_score
        low  = compute_learning_velocity_score(['python'], 5.0)       # 0.2/yr
        high = compute_learning_velocity_score(['python','react','sql','docker','git','aws'], 1.0)  # 6/yr
        self.assertGreater(high, low)

    def test_lv_score_caps_at_100(self):
        """LV should never exceed 100 regardless of inputs."""
        from neurohire.analysis_engine import compute_learning_velocity_score
        score = compute_learning_velocity_score([f's{i}' for i in range(100)], 0.5)
        self.assertLessEqual(score, 100.0)

    def test_lv_score_handles_zero_experience(self):
        """Zero experience years should not cause division by zero."""
        from neurohire.analysis_engine import compute_learning_velocity_score
        score = compute_learning_velocity_score(['python', 'sql'], 0.0)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

    def test_full_pipeline_produces_consistent_final_fit(self):
        """High SS + high AS should always produce High final fit."""
        from neurohire.analysis_engine import compute_analytical_score, compute_final_score, compute_final_fit
        ss = 85.0
        analytical = compute_analytical_score(90, 80, 75)
        fs = compute_final_score(ss, analytical)
        fit = compute_final_fit(fs)
        self.assertEqual(fit, 'High')

    def test_low_ss_high_as_averages_to_medium(self):
        """Low semantic + high analytical averages to Medium, not Low."""
        from neurohire.analysis_engine import compute_analytical_score, compute_final_score, compute_final_fit
        ss = 30.0  # low semantic match
        analytical = compute_analytical_score(85, 80, 75)  # high analytical
        fs = compute_final_score(ss, analytical)
        # FS = 0.5*30 + 0.5*80 = 55 => Medium
        self.assertEqual(fit := compute_final_fit(fs), 'Medium')


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