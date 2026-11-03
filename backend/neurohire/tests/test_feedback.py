"""
Task 4 tests — recruiter-feedback weight update (paper §IV.H).

Run:  python manage.py test neurohire.test_feedback
"""
import json
import os
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings

from neurohire import feedback as fb
from neurohire.models import AIDecisionLog, UserProfile

TRUSTED = 'https://neurohire-bay.vercel.app'


class InMemory:
    """Run feedback without MongoDB (in-memory state), reset per test."""

    def setUp(self):
        fb._memory_state.clear()
        p = patch.object(fb, '_collections', return_value=(None, None))
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(fb._memory_state.clear)


class RuleTests(SimpleTestCase):

    def test_signal_table(self):
        self.assertEqual(fb.feedback_signal('hire', 80, 60), 1)      # hired, SS dominated → toward SS
        self.assertEqual(fb.feedback_signal('hire', 50, 70), -1)     # hired, AS dominated → toward AS
        self.assertEqual(fb.feedback_signal('reject', 80, 60), -1)   # rejected, SS dominated → away from SS
        self.assertEqual(fb.feedback_signal('reject', 50, 70), 1)
        self.assertEqual(fb.feedback_signal('HIRE', 80, 60), 1)      # case-insensitive
        self.assertEqual(fb.feedback_signal('waitlist', 80, 60), 0)
        self.assertEqual(fb.feedback_signal('hire', 70, 70), 0)
        self.assertEqual(fb.feedback_signal('hire', None, 70), 0)

    def test_apply_signal_moves_by_eta_and_normalises(self):
        w = fb.apply_signal(0.6, 1, eta=0.05)
        self.assertEqual(w, {'w_ss': 0.65, 'w_as': 0.35})
        self.assertAlmostEqual(w['w_ss'] + w['w_as'], 1.0)

    def test_clipping(self):
        self.assertEqual(fb.apply_signal(0.88, 1, eta=0.05)['w_ss'], 0.9)
        self.assertEqual(fb.apply_signal(0.12, -1, eta=0.05)['w_ss'], 0.1)
        self.assertEqual(fb.apply_signal(0.9, 1, eta=0.05)['w_as'], 0.1)


class RecordFeedbackTests(InMemory, SimpleTestCase):

    def test_hire_updates_and_versions(self):
        r = fb.record_feedback('hire', 80, 60)
        self.assertTrue(r['updated'])
        self.assertEqual(r['after']['w_ss'], 0.65)
        self.assertEqual(r['after']['version'], 1)
        self.assertEqual(fb.get_learned_weights()['w_ss'], 0.65)

    def test_neutral_and_missing_do_not_update(self):
        self.assertFalse(fb.record_feedback('waitlist', 80, 60)['updated'])
        self.assertFalse(fb.record_feedback('hire', None, 60)['updated'])
        self.assertFalse(fb.record_feedback('hire', 60, 60)['updated'])
        self.assertEqual(fb.get_learned_weights()['w_ss'], 0.6)

    def test_changing_decision_reverses_previous_update(self):
        fb.record_feedback('hire', 80, 60)                                   # 0.60 → 0.65
        fb.record_feedback('reject', 80, 60, previous_decision='hire')        # s = −1 − (+1) = −2
        self.assertEqual(fb.get_learned_weights()['w_ss'], 0.55)             # same as a plain reject

    def test_hire_to_waitlist_undoes_update(self):
        fb.record_feedback('hire', 80, 60)
        fb.record_feedback('waitlist', 80, 60, previous_decision='hire')
        self.assertEqual(fb.get_learned_weights()['w_ss'], 0.6)

    def test_reset(self):
        fb.record_feedback('hire', 80, 60)
        fb.reset_weights()
        self.assertEqual(fb.get_learned_weights()['w_ss'], 0.6)


class PersistenceTests(SimpleTestCase):

    def test_saved_to_mongo_with_history(self):
        state, history = MagicMock(), MagicMock()
        state.find_one.return_value = {'_id': 'current', 'w_ss': 0.6, 'w_as': 0.4, 'version': 3}
        with patch.object(fb, '_collections', return_value=(state, history)):
            r = fb.record_feedback('reject', 90, 50, context={'candidate_ref': 'c1'})
        self.assertEqual(r['after']['version'], 4)
        args = state.update_one.call_args
        self.assertEqual(args[0][0], {'_id': 'current'})
        self.assertEqual(args[0][1]['$set']['w_ss'], 0.55)
        self.assertTrue(args.kwargs.get('upsert'))
        h = history.insert_one.call_args[0][0]
        self.assertEqual((h['s'], h['before']['w_ss'], h['after']['w_ss']), (-1, 0.6, 0.55))
        self.assertEqual(h['context'], {'candidate_ref': 'c1'})


class ScoringWeightsTests(InMemory, SimpleTestCase):

    def test_configured_by_default(self):
        fb.record_feedback('hire', 80, 60)
        with patch.dict(os.environ, {'ADAPTIVE_WEIGHTS': '0'}):
            self.assertEqual(fb.get_scoring_weights(), {'w_ss': 0.6, 'w_as': 0.4, 'source': 'configured'})

    def test_learned_when_enabled(self):
        fb.record_feedback('hire', 80, 60)
        with patch.dict(os.environ, {'ADAPTIVE_WEIGHTS': '1'}):
            self.assertEqual(fb.get_scoring_weights(), {'w_ss': 0.65, 'w_as': 0.35, 'source': 'learned'})
            from neurohire.analysis_engine import compute_final_score
            self.assertEqual(compute_final_score(80, 60), round(0.65 * 80 + 0.35 * 60, 2))


@override_settings(CORS_ALLOWED_ORIGINS=[TRUSTED])
class DecisionEndpointTests(InMemory, TestCase):

    def setUp(self):
        super().setUp()
        User = get_user_model()
        self.client = Client(enforce_csrf_checks=True)
        self.rec = User.objects.create_user('rec@company.com', 'rec@company.com', 'pw-12345678')
        UserProfile.objects.create(user=self.rec, role='recruiter')
        self.client.force_login(self.rec)

    def _post(self, body):
        return self.client.post('/api/ai-decision-logs/', json.dumps(body), content_type='application/json',
                                HTTP_ORIGIN=TRUSTED)

    def _body(self, **kw):
        return {'candidate_name': 'Asha', 'ai_recommendation': 'hire', 'recruiter_decision': 'hire', **kw}

    @patch('neurohire.views.mongo_get_candidate',
           return_value={'semantic_score': 82.0, 'analytical_score': 61.0, 'final_score': 73.6})
    def test_mongo_id_accepted_and_scores_from_candidate(self, _get):
        resp = self._post(self._body(candidate='65f0c0ffee0000000000abcd', role_match_score=82))
        self.assertEqual(resp.status_code, 201, resp.content)
        log = AIDecisionLog.objects.get()
        self.assertIsNone(log.candidate)
        self.assertEqual(log.candidate_ref, '65f0c0ffee0000000000abcd')
        self.assertTrue(log.is_agreement)
        self.assertEqual((log.semantic_score, log.analytical_score), (82.0, 61.0))
        self.assertEqual(log.weight_update['score_source'], 'candidate')
        self.assertTrue(log.weight_update['updated'])
        self.assertEqual(log.weight_update['w_ss_after'], 0.65)

    @patch('neurohire.views.mongo_get_candidate', return_value=None)
    @patch('neurohire.views.mongo_get_ranking', return_value={'results': [
        {'candidate_id': 'c9', 'semantic_score': 40.0, 'analytical_score': 75.0, 'final_score': 54.0}]})
    def test_scores_from_ranking_run_first(self, _rank, _cand):
        resp = self._post(self._body(candidate='c9', ranking_id='r1', recruiter_decision='reject'))
        self.assertEqual(resp.status_code, 201, resp.content)
        log = AIDecisionLog.objects.get()
        self.assertEqual(log.weight_update['score_source'], 'ranking')
        self.assertEqual(log.weight_update['s'], 1)                  # reject, AS dominated → toward SS
        self.assertFalse(log.is_agreement)

    @patch('neurohire.views.mongo_get_candidate', return_value=None)
    def test_portal_candidate_uses_request_scores(self, _cand):
        resp = self._post(self._body(candidate='portal_0_123', semantic_score=70, analytical_score=50))
        self.assertEqual(resp.status_code, 201, resp.content)
        log = AIDecisionLog.objects.get()
        self.assertEqual(log.weight_update['score_source'], 'request')
        self.assertTrue(log.weight_update['updated'])

    @patch('neurohire.views.mongo_get_candidate', return_value=None)
    def test_old_frontend_payload_still_logs(self, _cand):
        """Before Task 5 the card only sends role_match_score: logged, no update."""
        resp = self._post(self._body(candidate='portal_0_1', role_match_score=80, consistency_score=90,
                                     notes='Portal: LinkedIn'))
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertFalse(AIDecisionLog.objects.get().weight_update['updated'])

    @patch('neurohire.views.mongo_get_candidate', return_value=None)
    def test_changed_decision_reverses(self, _cand):
        self._post(self._body(candidate='x1', semantic_score=80, analytical_score=60))
        log = AIDecisionLog.objects.get()
        resp = self.client.patch(f'/api/ai-decision-logs/{log.pk}/', json.dumps({'recruiter_decision': 'reject'}),
                                 content_type='application/json', HTTP_ORIGIN=TRUSTED)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(fb.get_learned_weights()['w_ss'], 0.55)

    def test_weights_endpoint(self):
        fb.record_feedback('hire', 80, 60)
        body = self.client.get('/api/feedback/weights/').json()
        self.assertEqual(body['learned']['w_ss'], 0.65)
        self.assertEqual(body['configured'], {'w_ss': 0.6, 'w_as': 0.4})
        self.assertFalse(body['adaptive_enabled'])
        self.assertEqual(body['in_use']['source'], 'configured')

    def test_reset_is_staff_only(self):
        resp = self.client.post('/api/feedback/weights/reset/', '{}', content_type='application/json',
                                HTTP_ORIGIN=TRUSTED)
        self.assertEqual(resp.status_code, 403)
        self.rec.is_staff = True
        self.rec.save()
        resp = self.client.post('/api/feedback/weights/reset/', '{}', content_type='application/json',
                                HTTP_ORIGIN=TRUSTED)
        self.assertEqual(resp.status_code, 200)
