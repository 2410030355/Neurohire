"""
NeuroHire test suite.

Run all:      python manage.py test neurohire
One file:     python manage.py test neurohire.tests.test_scoring

  test_core.py        consistency, skill validation, similarity, formulas, security (Task 0)
  test_extraction.py  skills, experience dates, education, redaction, Gemini (Task 1)
  test_scoring.py     SS, CS, VS, LV, AS, FS exactly as in the paper (Task 2)
  test_ranking.py     ranking, embedding cache, deduplication, endpoints (Task 3)
  test_feedback.py    recruiter-feedback weight rule (Task 4)

Tests never call Gemini or a real MongoDB: settings.py disables both when it
detects a test run, so results are deterministic on any machine.
"""
