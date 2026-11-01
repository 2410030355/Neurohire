"""
Task 1 tests — résumé information extraction (paper §IV.B).

Run:  python manage.py test neurohire.test_extraction
"""
import os
import tempfile
from datetime import date
from unittest.mock import patch, MagicMock

from django.test import SimpleTestCase

from neurohire import extraction as ex

TODAY = date(2026, 11, 1)

SAMPLE_CV = """PRIYA NAIR
priya.nair@gmail.com | +91 98765 43210 | linkedin.com/in/priya-nair | github.com/priyan
Date of Birth: 12/03/1998
Gender: Female
SUMMARY
Senior frontend engineer with 5+ years of experience building React apps. She leads UI teams.
SKILLS
JavaScript, TypeScript, React, Next.js, Redux, HTML5, CSS3, Tailwind CSS, Jest, Cypress, Webpack, Git
EXPERIENCE
Senior Frontend Engineer, Flipkart | Jan 2023 – Present
- Built a design system in React and TypeScript; wrote unit tests with Jest
Frontend Engineer, TCS | Jul 2020 - Dec 2022
- Developed dashboards using Redux; migrated legacy JS to TS
Intern, Startup X | May 2020 – Aug 2020
EDUCATION
B.Tech Computer Science, VIT Vellore | 2016 - 2020 | CGPA 8.4
PROJECTS
Portfolio site (Next.js) 2019 - 2020
"""


class SkillExtractionTests(SimpleTestCase):

    def test_frontend_skills_detected(self):
        skills = ex.extract_skills(SAMPLE_CV)
        for s in ["javascript", "typescript", "react", "next.js", "redux", "html", "css",
                  "tailwind", "jest", "cypress", "webpack", "git"]:
            self.assertIn(s, skills)

    def test_symbol_skills(self):
        skills = ex.extract_skills("Languages: C++, C#, Java\nFrameworks: .NET Core, ASP.NET, Node.js")
        for s in ["c++", "c#", "java", ".net", "asp.net", "node.js"]:
            self.assertIn(s, skills)

    def test_java_not_matched_inside_javascript(self):
        self.assertNotIn("java", ex.extract_skills("Built SPAs in JavaScript and TypeScript"))

    def test_go_and_r_need_context(self):
        prose = "I go to meetups. Ready to go live. Worked in R&D with Python."
        skills = ex.extract_skills(prose)
        self.assertNotIn("golang", skills)
        self.assertNotIn("r", skills)
        self.assertIn("golang", ex.extract_skills("Languages: Go, Python, Java"))
        self.assertIn("golang", ex.extract_skills("Wrote services in Golang"))
        self.assertIn("r", ex.extract_skills("Data tools: R, Python, SQL, Pandas"))
        self.assertIn("r", ex.extract_skills("Statistical modelling in R programming"))

    def test_generic_words_are_not_skills(self):
        skills = ex.extract_skills("Backend and frontend testing, API design, less than 2 weeks, "
                                   "Spring 2023 semester, express interest")
        for s in ["less", "spring boot", "express"]:
            self.assertNotIn(s, skills)

    def test_weak_alias_needs_a_companion_skill(self):
        self.assertNotIn("jest", ex.extract_skills("He said it in jest."))
        self.assertIn("jest", ex.extract_skills("Tested React components with Jest"))

    def test_aliases_map_to_canonical(self):
        skills = ex.extract_skills("ReactJS, K8s, Postgres, sklearn")
        for s in ["react", "kubernetes", "postgresql", "scikit-learn"]:
            self.assertIn(s, skills)

    def test_find_skill_spans_symbol_safe(self):
        text = "javascript developer; also java"
        spans = ex.find_skill_spans(text, "java")
        self.assertEqual(len(spans), 1)
        self.assertEqual(text[spans[0][0]:spans[0][1]], "java")

    def test_merge_keeps_only_gemini_skills_written_in_text(self):
        text = "Languages: Java, SQL. Used Postman for API tests."
        skills, other = ex.merge_skills(text, ex.extract_skills(text),
                                        ["Java", "Kubernetes", "Postman", "Figma", "C"])
        self.assertIn("java", skills)
        self.assertNotIn("kubernetes", skills)   # not in the résumé
        self.assertNotIn("c", skills)            # ambiguous: only via context rules
        self.assertEqual(other, ["Postman"])     # non-catalog, but present in text


class ExperienceTests(SimpleTestCase):

    def test_date_ranges_with_overlap_and_present(self):
        exp = ex.extract_experience(SAMPLE_CV, today=TODAY)
        # May 2020 → Nov 2026 continuous (intern overlaps TCS start)
        self.assertEqual(exp["dated_years"], 6.6)
        self.assertEqual(exp["claimed_years"], 5.0)
        self.assertEqual(exp["source"], "dated")
        self.assertEqual(len(exp["positions"]), 3)
        self.assertIn("Flipkart", exp["positions"][0]["title"])

    def test_education_and_project_dates_ignored(self):
        exp = ex.extract_experience(SAMPLE_CV, today=TODAY)
        starts = {p["start"] for p in exp["positions"]}
        self.assertNotIn("2016-07", starts)   # B.Tech 2016-2020
        self.assertNotIn("2019-07", starts)   # project 2019-2020

    def test_formats(self):
        text = ("Experience\nAcme 2018-2021\nBeta 03/2021 to 06/2023\nGamma Sept 2023 - current\n"
                "Delta 2023-07 – 2023-12\nEpsilon Jan '24 - Mar '24")
        exp = ex.extract_experience(text, today=TODAY)
        self.assertEqual(len(exp["positions"]), 5)
        self.assertEqual(exp["positions"][1]["months"], 28)

    def test_no_heading_skips_education_lines(self):
        exp = ex.extract_experience("B.Tech, JNTU 2017 - 2021\nInternship at X Jun 2021 - Aug 2021", today=TODAY)
        self.assertEqual(len(exp["positions"]), 1)
        self.assertEqual(exp["positions"][0]["months"], 3)

    def test_claimed_only(self):
        exp = ex.extract_experience("QA engineer with 7 years of hands-on experience.", today=TODAY)
        self.assertIsNone(exp["dated_years"])
        self.assertEqual(exp["years"], 7.0)
        self.assertEqual(exp["source"], "claimed")

    def test_bare_years_are_not_experience(self):
        exp = ex.extract_experience("4 years B.Tech programme. Age 23 years.", today=TODAY)
        self.assertIsNone(exp["years"])
        self.assertEqual(exp["source"], "none")

    def test_future_end_is_capped_at_today(self):
        exp = ex.extract_experience("Experience\nAcme Jan 2026 - Dec 2030", today=TODAY)
        self.assertEqual(exp["positions"][0]["months"], 11)

    def test_merge_months(self):
        self.assertEqual(ex.merge_months([(0, 12), (6, 18), (24, 30)]), 24)

    def test_positions_from_gemini(self):
        years = ex.experience_from_positions(
            [{"start": "Jan 2020", "end": "Present"}, {"start": "2021", "end": None}], today=TODAY)
        self.assertEqual(years, 6.9)


class EducationTests(SimpleTestCase):

    def test_highest_degree(self):
        self.assertEqual(ex.extract_education("B.Tech 2019, M.Tech 2021"), "Master's Degree")
        self.assertEqual(ex.extract_education("PhD in CS"), "PhD")
        self.assertEqual(ex.extract_education("BCA from Osmania"), "Bachelor's Degree")

    def test_job_titles_are_not_degrees(self):
        self.assertIsNone(ex.extract_education("Scrum Master. Associate Software Engineer. Mastered React."))


class RedactionTests(SimpleTestCase):

    def test_contact_and_personal_fields_removed(self):
        out = ex.redact_for_embedding(SAMPLE_CV, name="Priya Nair")
        for leaked in ["priya", "Priya", "PRIYA", "NAIR", "gmail", "98765", "linkedin", "github.com",
                       "Date of Birth", "Female"]:
            self.assertNotIn(leaked, out)
        self.assertIn("React", out)
        self.assertIn("Jan 2023", out)     # dates are not phone numbers

    def test_blind_mode_removes_pronouns(self):
        out = ex.redact_for_embedding("She leads teams. Mr. Rao mentored her.", blind=True)
        self.assertNotIn("She", out)
        self.assertNotIn("her", out)
        self.assertNotIn("Mr", out)
        self.assertIn("leads teams", out)

    def test_name_that_is_a_skill_word_is_kept_as_skill(self):
        out = ex.redact_for_embedding("Taylor Swift\nSkills: Swift, Kotlin", name="Taylor Swift")
        self.assertNotIn("Taylor", out)
        self.assertIn("Swift, Kotlin", out)

    def test_ordinary_words_survive(self):
        out = ex.redact_for_embedding("Addressed performance issues. Pan-India rollout. Agile team.")
        self.assertIn("Addressed performance", out)
        self.assertIn("Pan-India", out)


class GeminiExtractionTests(SimpleTestCase):

    def _client(self, text=None, error=None):
        client = MagicMock()
        if error:
            client.models.generate_content.side_effect = error
        else:
            client.models.generate_content.return_value = MagicMock(text=text)
        return client

    def test_structured_output_normalised(self):
        payload = ('{"name":"A B","email":"","skills":["React"],"employment":[{"title":"Dev",'
                   '"company":"X","start":"Jan 2020","end":"Present","skills_used":[]}],'
                   '"education":[],"projects":[],"claimed_experience_years":0}')
        with patch.object(ex, "get_gemini_client", return_value=self._client(payload)), \
                patch.object(ex, "GEMINI_EXTRACTION_ENABLED", True):
            r = ex.extract_with_gemini("some resume")
        self.assertEqual(r["name"], "A B")
        self.assertIsNone(r["email"])                      # "" → None
        self.assertIsNone(r["claimed_experience_years"])   # 0 → None
        self.assertEqual(r["employment"][0]["company"], "X")

    def test_request_uses_json_schema_and_zero_temperature(self):
        client = self._client('{"skills":[],"employment":[],"education":[],"projects":[]}')
        with patch.object(ex, "get_gemini_client", return_value=client), \
                patch.object(ex, "GEMINI_EXTRACTION_ENABLED", True):
            ex.extract_with_gemini("resume")
        config = client.models.generate_content.call_args.kwargs["config"]
        self.assertEqual(config["response_mime_type"], "application/json")
        self.assertIn("response_json_schema", config)
        self.assertEqual(config["temperature"], 0)

    def test_timeout_stops_further_attempts(self):
        client = self._client(error=TimeoutError("Request timed out"))
        with patch.object(ex, "get_gemini_client", return_value=client), \
                patch.object(ex, "GEMINI_EXTRACTION_ENABLED", True):
            self.assertIsNone(ex.extract_with_gemini("resume"))
        self.assertEqual(client.models.generate_content.call_count, 1)

    def test_disabled_by_env_flag(self):
        with patch.object(ex, "GEMINI_EXTRACTION_ENABLED", False), \
                patch.object(ex, "get_gemini_client") as gc:
            self.assertIsNone(ex.extract_with_gemini("resume"))
        gc.assert_not_called()

    def test_client_gets_timeout_in_milliseconds(self):
        fake_genai = MagicMock()
        with patch.dict(os.environ, {"GEMINI_API_KEY": "k"}), \
                patch.dict("sys.modules", {"google": MagicMock(genai=fake_genai), "google.genai": fake_genai}), \
                patch.object(ex, "_gemini_client", None), patch.object(ex, "GEMINI_TIMEOUT_SECONDS", 15):
            ex.get_gemini_client()
            kwargs = fake_genai.Client.call_args.kwargs
        self.assertEqual(kwargs["http_options"], {"timeout": 15000})


class AnalyzeResumeIntegrationTests(SimpleTestCase):
    """End-to-end on a real .docx with Gemini off (deterministic regex path)."""

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
    @patch("neurohire.analysis_engine.get_similarity_score", return_value=60.0)
    def test_docx_pipeline(self, sim, _g):
        from neurohire.analysis_engine import analyze_resume
        r = analyze_resume(self._docx(SAMPLE_CV), "Senior Frontend Developer", "React TypeScript engineer")
        self.assertEqual(r["name"], "Priya Nair")
        self.assertIn("react", r["skills"])
        self.assertGreater(r["experience_years"], 6)
        self.assertEqual(r["experience_source"], "dated")
        self.assertEqual(r["experience_years_claimed"], 5.0)
        self.assertEqual(len(r["employment_history"]), 3)
        self.assertEqual(r["education"], "Bachelor's Degree")
        self.assertEqual(r["extraction_method"], "regex")
        # Similarity received redacted text only
        embedded_text = sim.call_args[0][0]
        for leaked in ["priya", "nair", "gmail", "98765", "female", "date of birth"]:
            self.assertNotIn(leaked, embedded_text)


class AnnotationStrippingTests(SimpleTestCase):
    """Evaluation résumés carry their own label; it must never reach scoring."""

    def test_label_lines_removed(self):
        text = "Jane Doe\nGround Truth Label: Relevant\nground_truth: 1\nRelevance label - high\nReact developer"
        out = ex.strip_annotation_lines(text)
        self.assertNotIn("Relevant", out)
        self.assertNotIn("ground", out.lower())
        self.assertIn("React developer", out)

    def test_ordinary_lines_untouched(self):
        text = "Worked on ground-up rewrite of the truth table UI"
        self.assertEqual(ex.strip_annotation_lines(text), text)

    @patch("neurohire.analysis_engine.extract_with_gemini", return_value=None)
    @patch("neurohire.analysis_engine.get_similarity_score", return_value=60.0)
    def test_label_never_reaches_similarity(self, sim, _g):
        from neurohire.analysis_engine import analyze_resume
        path = AnalyzeResumeIntegrationTests()._docx.__func__(self, SAMPLE_CV + "\nGround Truth Label: Highly Relevant")
        analyze_resume(path, "Senior Frontend Developer", "React engineer")
        self.assertNotIn("ground truth", sim.call_args[0][0])
        self.assertNotIn("highly relevant", sim.call_args[0][0])


class EmbeddingCallTests(SimpleTestCase):

    def _client(self, vectors):
        client = MagicMock()
        client.models.embed_content.return_value = MagicMock(
            embeddings=[MagicMock(values=v) for v in vectors])
        return client

    def test_one_batched_call_for_resume_and_jd(self):
        from neurohire import analysis_engine as ae
        client = self._client([[1.0, 0.0], [1.0, 0.0]])
        with patch.object(ae, "_get_gemini_client", return_value=client):
            score = ae.get_similarity_score("react developer", "react engineer")
        self.assertAlmostEqual(score, 100.0, places=4)
        client.models.embed_content.assert_called_once()
        kwargs = client.models.embed_content.call_args.kwargs
        self.assertEqual(kwargs["contents"], ["react developer", "react engineer"])
        self.assertEqual(kwargs["config"], {"task_type": "SEMANTIC_SIMILARITY"})

    def test_falls_back_to_tfidf_when_gemini_unavailable(self):
        from neurohire import analysis_engine as ae
        with patch.object(ae, "_get_gemini_client", return_value=None):
            same = ae.get_similarity_score("react typescript redux", "react typescript redux")
            other = ae.get_similarity_score("react typescript redux", "oracle cobol mainframe")
        self.assertGreater(same, other)

    def test_malformed_response_falls_back(self):
        from neurohire import analysis_engine as ae
        client = self._client([[1.0, 0.0]])  # one vector for two texts
        with patch.object(ae, "_get_gemini_client", return_value=client), \
                patch.object(ae, "_tfidf_similarity", return_value=12.0) as tf:
            self.assertEqual(ae.get_similarity_score("a b", "c d"), 12.0)
        tf.assert_called_once()
