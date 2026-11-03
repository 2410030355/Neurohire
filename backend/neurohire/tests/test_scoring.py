"""
Task 2 tests — scoring exactly as the paper defines it (§IV.C–E).

Run:  python manage.py test neurohire.test_scoring
"""
import os
import tempfile
from unittest.mock import patch

from django.test import SimpleTestCase

from neurohire import scoring as sc
from neurohire.extraction import extract_experience, extract_skills, _heading_kind
from datetime import date

TODAY = date(2026, 11, 1)


class SemanticScoreTests(SimpleTestCase):

    def test_cosine_times_100_clipped(self):
        self.assertEqual(sc.similarity_to_score(0.734), 73.4)
        self.assertEqual(sc.similarity_to_score(-0.2), 0.0)
        self.assertEqual(sc.similarity_to_score(1.0000001), 100.0)


class SkillValidationScoreTests(SimpleTestCase):

    def _c(self, *statuses):
        return [{'skill': f's{i}', 'status': st} for i, st in enumerate(statuses)]

    def test_vs_is_valid_over_total(self):
        self.assertEqual(sc.compute_skill_validation(self._c('Valid', 'Partial', 'Unverified', 'Valid')), 50.0)

    def test_partial_and_unverified_do_not_count(self):
        self.assertEqual(sc.compute_skill_validation(self._c('Partial', 'Unverified')), 0.0)

    def test_no_skills_is_none_not_zero(self):
        self.assertIsNone(sc.compute_skill_validation([]))

    def test_bands(self):
        self.assertEqual(sc.evidence_band(71), 'Stronger evidence')
        self.assertEqual(sc.evidence_band(70), 'Mixed evidence')
        self.assertEqual(sc.evidence_band(40), 'Mixed evidence')
        self.assertEqual(sc.evidence_band(39.9), 'Weaker evidence')
        self.assertEqual(sc.evidence_band(None), 'Not available')

    def test_verb_inflections(self):
        for text in ("led the react migration", "building react apps", "react ui we deployed",
                     "configured webpack for react"):
            spans = [(text.index('react'), text.index('react') + 5)]
            self.assertEqual(sc.classify_skill_evidence('react', spans, text)['status'], 'Valid', text)

    def test_any_mode_checks_every_mention(self):
        text = "Skills: React, Redux\n" + "x" * 80 + "\nBuilt the checkout UI in React"
        spans = [(text.index('React'), text.index('React') + 5),
                 (text.rindex('React'), text.rindex('React') + 5)]
        self.assertEqual(sc.classify_skill_evidence('react', spans, text, mode='first')['status'], 'Partial')
        self.assertEqual(sc.classify_skill_evidence('react', spans, text, mode='any')['status'], 'Valid')

    def test_window_is_60_characters(self):
        far = "built " + "x" * 70 + " react"
        near = "built " + "x" * 50 + " react"
        self.assertEqual(sc.classify_skill_evidence('react', [(far.index('react'), len(far))], far)['status'],
                         'Unverified')
        self.assertEqual(sc.classify_skill_evidence('react', [(near.index('react'), len(near))], near)['status'],
                         'Valid')


TIMELINE_CV = """EXPERIENCE
Frontend Engineer, TCS | Jan 2019 - Dec 2020
- Developed dashboards with JavaScript, HTML and CSS
Senior Frontend Engineer, Flipkart | Jan 2021 - Dec 2022
- Built a design system in React and TypeScript; wrote tests with Jest
EDUCATION
B.Tech, VIT | 2015 - 2019
"""


class LearningVelocityTests(SimpleTestCase):

    def _lv(self, text):
        pos = extract_experience(text, today=TODAY)['positions']
        tl = sc.skill_timeline(text, pos, extract_skills, heading_fn=_heading_kind)
        return sc.compute_learning_velocity_raw(tl)

    def test_new_skills_over_span(self):
        r = self._lv(TIMELINE_CV)
        # baseline (TCS): javascript, html, css. New at Flipkart: react, typescript, jest = 3
        self.assertEqual(sorted(r['new_skills']), ['jest', 'react', 'typescript'])
        self.assertEqual(r['span_years'], 4.0)          # Jan 2019 – Dec 2022
        self.assertAlmostEqual(r['raw'], 0.75)          # 3 / 4

    def test_education_block_not_attributed(self):
        r = self._lv(TIMELINE_CV + "Coursework: Python, Kubernetes\n")
        self.assertNotIn('python', r['new_skills'])

    def test_single_position_is_insufficient(self):
        r = self._lv("EXPERIENCE\nEngineer, X | Jan 2020 - Dec 2022\n- Built React apps\n")
        self.assertIsNone(r['raw'])
        self.assertEqual(r['basis'], 'insufficient dated history')

    def test_positions_without_skills_are_insufficient(self):
        r = self._lv("EXPERIENCE\nClerk, A | 2015 - 2017\nClerk, B | 2017 - 2019\n")
        self.assertIsNone(r['raw'])

    def test_min_max_normalisation(self):
        self.assertEqual(sc.normalize_min_max(2.0, 0.0, 4.0), 0.5)
        self.assertEqual(sc.normalize_min_max(9.0, 0.0, 4.0), 1.0)     # clipped
        self.assertEqual(sc.normalize_min_max(1.0, 1.0, 1.0), 0.5)     # equal bounds
        self.assertIsNone(sc.normalize_min_max(None, 0.0, 4.0))

    def test_batch_normalisation(self):
        self.assertEqual(sc.normalize_lv_batch([0.5, None, 1.5, 1.0]), [0.0, None, 1.0, 0.5])
        self.assertEqual(sc.normalize_lv_batch([None, None]), [None, None])

    def test_labels(self):
        self.assertEqual(sc.lv_label(None), 'N/A')
        self.assertEqual(sc.lv_label(80), 'High')
        self.assertEqual(sc.lv_label(50), 'Medium')
        self.assertEqual(sc.lv_label(10), 'Low')


class AggregationTests(SimpleTestCase):

    def test_as_mean_of_three(self):
        self.assertEqual(sc.compute_analytical(90, 60, 30)['score'], 60.0)

    def test_as_mean_of_available_and_lists_missing(self):
        r = sc.compute_analytical(90, None, 30)
        self.assertEqual(r['score'], 60.0)
        self.assertEqual(r['missing'], ['VS'])

    def test_fs_paper_weights(self):
        r = sc.compute_final(80, 50)
        self.assertEqual(r['score'], 68.0)
        self.assertEqual(r['weights'], {'SS': 0.6, 'AS': 0.4})

    def test_fs_without_as_uses_ss(self):
        self.assertEqual(sc.compute_final(80, None)['score'], 80.0)

    def test_fs_without_ss_uses_as(self):
        self.assertEqual(sc.compute_final(None, 55)['score'], 55.0)

    def test_score_candidate_lv_scaled_to_100(self):
        r = sc.score_candidate(ss=70, cs=100, vs=50, lv_raw=2.0)   # LV = 2/4 → 0.5 → 50
        self.assertEqual(r['lv_score'], 50.0)
        self.assertEqual(r['analytical_score'], round((100 + 50 + 50) / 3, 2))
        self.assertEqual(r['final_score'], round(0.6 * 70 + 0.4 * r['analytical_score'], 2))

    def test_score_candidate_uses_batch_lv_when_given(self):
        r = sc.score_candidate(ss=70, cs=100, vs=50, lv_raw=2.0, lv_norm=1.0)
        self.assertEqual(r['lv_score'], 100.0)

    def test_weights_configurable(self):
        self.assertEqual(sc.compute_final(80, 40, w_ss=0.5, w_as=0.5)['score'], 60.0)


class AnalyzeResumeScoringTests(SimpleTestCase):
    """End-to-end: every paper component is present and consistent."""

    def _docx(self, text):
        import docx
        d = docx.Document()
        for line in text.splitlines():
            d.add_paragraph(line)
        f = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
        d.save(f.name)
        self.addCleanup(os.remove, f.name)
        return f.name

    @patch("neurohire.analysis_engine.extract_with_gemini", return_value=None)
    @patch("neurohire.analysis_engine.get_similarity_details",
           return_value={"score": 65.0, "cosine": 0.65, "method": "gemini"})
    def test_breakdown(self, _sim, _g):
        from neurohire.analysis_engine import analyze_resume
        cv = "Asha Rao\nasha@example.com\nSKILLS\nJavaScript, React, TypeScript, Jest, HTML, CSS\n" + TIMELINE_CV
        r = analyze_resume(self._docx(cv), "Senior Frontend Developer",
                           "Senior frontend developer: React, TypeScript, Next.js, GraphQL")
        self.assertEqual(r['semantic_score'], 65.0)
        self.assertEqual(r['role_match_score'], 65.0)
        self.assertEqual(r['consistency_score'], 100.0)
        self.assertIsNotNone(r['skill_validation_score'])
        self.assertAlmostEqual(r['lv_raw'], 0.75)
        self.assertEqual(r['lv_score'], round(0.75 / 4.0 * 100, 2))
        expected_as = round((r['consistency_score'] + r['skill_validation_score'] + r['lv_score']) / 3, 2)
        self.assertEqual(r['analytical_score'], expected_as)
        self.assertEqual(r['final_score'], round(0.6 * 65.0 + 0.4 * expected_as, 2))
        self.assertEqual(r['missing_components'], [])
        self.assertEqual(sorted(r['missing_skills']), ['graphql', 'next.js'])
        self.assertIn('Final score (FS)', r['explainability'])

    @patch("neurohire.analysis_engine.extract_with_gemini", return_value=None)
    @patch("neurohire.analysis_engine.get_similarity_details",
           return_value={"score": 50.0, "cosine": 0.5, "method": "tfidf"})
    def test_undated_resume_marks_components_missing(self, _sim, _g):
        from neurohire.analysis_engine import analyze_resume
        r = analyze_resume(self._docx("Ravi K\nSKILLS\nReact, Redux, Jest\nBuilt React apps."), "Frontend")
        self.assertIsNone(r['experience_years'])
        self.assertIsNone(r['lv_score'])
        self.assertEqual(r['learning_velocity'], 'N/A')
        self.assertIn('LV', r['missing_components'])
        # target role "Frontend" names no catalogue skills → JD-conditioned VS not computable
        self.assertIsNone(r['skill_validation_score'])
        self.assertIsNotNone(r['skill_validation_score_original'])
        self.assertEqual(r['analytical_components'], ['CS'])
        self.assertEqual(len(r['consistency_rules_skipped']), 2)


class EvidenceFixTests(SimpleTestCase):
    """Verbs inside skill names are not evidence; skills lists are not sentences."""

    def _status(self, text, skill, mode):
        from neurohire.extraction import find_skill_spans
        return sc.classify_skill_evidence(skill, find_skill_spans(text, skill), text, mode=mode)['status']

    def test_skill_name_containing_a_verb_is_not_evidence(self):
        text = "Skills: React, Responsive Design, Jest"
        self.assertEqual(self._status(text, 'react', 'first'), 'Unverified')

    def test_real_verb_still_counts_next_to_such_a_skill(self):
        text = "Built responsive design system pages in React"
        self.assertEqual(self._status(text, 'react', 'first'), 'Valid')

    def test_list_lines_never_count_in_sentence_mode(self):
        text = "SKILLS\nJava  •  React  •  Redux  •  Jest\nWORK\n• Designed Kafka pipelines"
        self.assertEqual(self._status(text, 'react', 'sentence'), 'Unverified')
        self.assertEqual(self._status(text, 'kafka', 'sentence'), 'Valid')

    def test_sentence_mode_uses_any_mention(self):
        text = ("Skills: React, Redux, Jest, CSS\n" + "Bengaluru, India. Open to relocation anywhere.\n"
                "• Led the move of checkout to React and Redux")
        self.assertEqual(self._status(text, 'react', 'sentence'), 'Valid')
        self.assertEqual(self._status(text, 'react', 'first'), 'Partial')   # 2 mentions, no verb near the first

    def test_is_list_line(self):
        self.assertTrue(sc.is_list_line("React • TypeScript • Redux • Jest"))
        self.assertTrue(sc.is_list_line("Java, Spring Boot, MySQL, Docker, Kafka"))
        self.assertFalse(sc.is_list_line("• Built a dashboard in React, Redux and Jest for 2M users"))

    def test_jd_conditioned_evidence(self):
        validated = [{'skill': 'react', 'status': 'Valid'}, {'skill': 'jest', 'status': 'Partial'},
                     {'skill': 'java', 'status': 'Valid'}]
        self.assertEqual(sc.compute_jd_evidence(validated, ['react', 'jest', 'typescript', 'redux']), 25.0)
        self.assertIsNone(sc.compute_jd_evidence(validated, []))



class RevisedMethodTests(SimpleTestCase):

    def test_cs_not_applicable_without_skills(self):
        r = sc.compute_consistency([], 3.0)
        self.assertIsNone(r['score'])
        self.assertTrue(r['not_applicable'])
        self.assertEqual(sc.compute_consistency([], 3.0, empty_not_applicable=False)['score'], 100.0)

    def test_no_skills_no_longer_gets_perfect_as(self):
        r = sc.score_candidate(ss=10, cs=None, vs=None, lv_raw=None)
        self.assertIsNone(r['analytical_score'])
        self.assertEqual(r['final_score'], 10.0)          # SS alone, not 0.6·10 + 0.4·100

    @patch("neurohire.analysis_engine.extract_with_gemini", return_value=None)
    @patch("neurohire.analysis_engine.get_similarity_details",
           return_value={"score": 40.0, "cosine": 0.4, "method": "tfidf"})
    def test_analysis_uses_jd_conditioned_vs(self, _s, _g):
        from neurohire.analysis_engine import analyze_text
        cv = ("Asha Rao\nSKILLS\nReact • Redux • Jest • Java\nEXPERIENCE\n"
              "• Built the checkout UI in React\n• Developed Jest tests for the cart")
        r = analyze_text(cv, 'Frontend', 'Frontend engineer: React, Redux, Jest, TypeScript')
        self.assertEqual(r['vs_definition'], 'jd')
        self.assertEqual(sorted(r['jd_skills_evidenced']), ['jest', 'react'])
        self.assertEqual(r['skill_validation_score'], 50.0)            # 2 of 4 JD skills evidenced
        self.assertIn('2 of 4 skills', r['explainability'])

    @patch("neurohire.analysis_engine.extract_with_gemini", return_value=None)
    @patch("neurohire.analysis_engine.get_similarity_details",
           return_value={"score": 40.0, "cosine": 0.4, "method": "tfidf"})
    def test_resume_without_skills(self, _s, _g):
        from neurohire.analysis_engine import analyze_text
        r = analyze_text("Ravi K\nManaged payroll and onboarding for 200 staff.", 'HR', 'Java developer: Java, Spring')
        self.assertIsNone(r['consistency_score'])                     # no skills: CS not applicable
        self.assertIn('not applicable', r['explainability'])
        self.assertEqual(r['skill_validation_score'], 0.0)              # JD asks for Java; none evidenced
        self.assertEqual(r['analytical_components'], ['VS'])
        self.assertEqual(r['final_score'], round(0.6 * 40 + 0.4 * 0, 2))  # not 0.6·40 + 0.4·100

    @patch("neurohire.analysis_engine.extract_with_gemini", return_value=None)
    @patch("neurohire.analysis_engine.get_similarity_details",
           return_value={"score": 40.0, "cosine": 0.4, "method": "tfidf"})
    def test_no_jd_skills_means_vs_not_available(self, _s, _g):
        from neurohire.analysis_engine import analyze_text
        r = analyze_text("Asha\nSKILLS\nReact, Redux\n• Built React apps", 'Senior Engineer', '')
        self.assertIsNone(r['skill_validation_score'])                  # role title names no skills
        self.assertIn('names no recognised skills', r['explainability'])
