"""
Task 6 tests — MongoDB helpers and feedback persistence (mocked collections).

Run:  python manage.py test neurohire.tests.test_storage
"""
from unittest.mock import MagicMock, patch

from bson import ObjectId
from django.test import SimpleTestCase

from neurohire import feedback as fb
from neurohire import mongo_client as mc


class ConnectionTests(SimpleTestCase):

    def test_unreachable_database_returns_none(self):
        with patch.object(mc, '_db', None), patch.object(mc, '_client', None):
            self.assertIsNone(mc._get_db())          # test settings point at 127.0.0.1:1
            self.assertFalse(mc.mongo_is_available())
            self.assertEqual(mc.mongo_all_candidates(), [])
            self.assertIsNone(mc.mongo_insert_candidate({'name': 'x'}))
            self.assertEqual(mc.mongo_candidates_for_ranking(), [])
            self.assertIsNone(mc.mongo_save_ranking({}))
            self.assertFalse(mc.mongo_update_candidate_status('x', 'scheduled'))


class RankingHelperTests(SimpleTestCase):

    def setUp(self):
        self.col = MagicMock()
        p = patch.object(mc, 'candidates_collection', return_value=self.col)
        p.start()
        self.addCleanup(p.stop)

    def test_only_candidates_with_text_are_rankable(self):
        oid = ObjectId()
        self.col.find.return_value.sort.return_value.limit.return_value = [{'_id': oid, 'name': 'A'}]
        docs = mc.mongo_candidates_for_ranking(limit=10)
        query = self.col.find.call_args[0][0]
        self.assertEqual(query, {'resume_text_redacted': {'$exists': True, '$nin': [None, '']}})
        self.assertEqual(docs, [{'id': str(oid), 'name': 'A'}])
        self.col.find.return_value.sort.return_value.limit.assert_called_once_with(10)

    def test_id_filter_skips_invalid_ids(self):
        good = ObjectId()
        self.col.find.return_value.sort.return_value.limit.return_value = []
        mc.mongo_candidates_for_ranking(ids=[str(good), 'portal_0_1', None])
        self.assertEqual(self.col.find.call_args[0][0]['_id'], {'$in': [good]})

    def test_set_embedding_cache(self):
        oid = ObjectId()
        mc.mongo_set_embedding_cache(str(oid), {'key': 'k', 'values': [1.0]})
        self.col.update_one.assert_called_once_with(
            {'_id': oid}, {'$set': {'embedding_cache': {'key': 'k', 'values': [1.0]}}})

    def test_empty_cache_not_written(self):
        mc.mongo_set_embedding_cache(str(ObjectId()), None)
        self.col.update_one.assert_not_called()

    def test_get_candidate_hides_internal_fields(self):
        oid = ObjectId()
        self.col.find_one.return_value = {'_id': oid, 'name': 'A'}
        doc = mc.mongo_get_candidate(str(oid))
        self.assertEqual(self.col.find_one.call_args[0][1], {'resume_text_redacted': 0, 'embedding_cache': 0})
        self.assertEqual(doc, {'mongo_id': str(oid), 'name': 'A'})

    def test_bad_candidate_id_returns_none(self):
        self.assertIsNone(mc.mongo_get_candidate('not-an-object-id'))

    def test_status_update(self):
        oid = ObjectId()
        self.col.update_one.return_value = MagicMock(matched_count=1)
        self.assertTrue(mc.mongo_update_candidate_status(str(oid), 'scheduled'))
        filt, upd = self.col.update_one.call_args[0]
        self.assertEqual(filt, {'_id': oid})
        self.assertEqual(upd['$set']['status'], 'scheduled')
        self.col.update_one.return_value = MagicMock(matched_count=0)
        self.assertFalse(mc.mongo_update_candidate_status(str(oid), 'scheduled'))


class RankingRunTests(SimpleTestCase):

    def test_save_and_get(self):
        col = MagicMock()
        oid = ObjectId()
        col.insert_one.return_value = MagicMock(inserted_id=oid)
        col.find_one.return_value = {'_id': oid, 'results': []}
        with patch.object(mc, 'rankings_collection', return_value=col):
            self.assertEqual(mc.mongo_save_ranking({'job_description': 'jd'}), str(oid))
            saved = col.insert_one.call_args[0][0]
            self.assertIn('created_at', saved)
            self.assertEqual(mc.mongo_get_ranking(str(oid)), {'ranking_id': str(oid), 'results': []})


class FeedbackPersistenceTests(SimpleTestCase):

    def _cols(self, current=None):
        state, history = MagicMock(), MagicMock()
        state.find_one.return_value = current
        return state, history

    def test_learned_weights_read_from_mongo(self):
        state, history = self._cols({'_id': 'current', 'w_ss': 0.7, 'w_as': 0.3, 'version': 5})
        with patch.object(fb, '_collections', return_value=(state, history)):
            w = fb.get_learned_weights()
        self.assertEqual((w['w_ss'], w['w_as'], w['version']), (0.7, 0.3, 5))

    def test_defaults_before_first_update(self):
        state, history = self._cols(None)
        with patch.object(fb, '_collections', return_value=(state, history)):
            self.assertEqual(fb.get_learned_weights(), {'w_ss': 0.6, 'w_as': 0.4, 'version': 0})

    def test_read_error_falls_back_to_defaults(self):
        state, history = self._cols()
        state.find_one.side_effect = RuntimeError('network')
        fb._memory_state.clear()
        with patch.object(fb, '_collections', return_value=(state, history)):
            self.assertEqual(fb.get_learned_weights()['w_ss'], 0.6)

    def test_history_sorted_newest_first(self):
        state, history = self._cols()
        history.find.return_value.sort.return_value.limit.return_value = [{'version': 2}, {'version': 1}]
        with patch.object(fb, '_collections', return_value=(state, history)):
            rows = fb.feedback_history(limit=5)
        history.find.return_value.sort.assert_called_once_with('version', -1)
        self.assertEqual(rows, [{'version': 2}, {'version': 1}])

    def test_reset_writes_defaults_and_history(self):
        state, history = self._cols({'_id': 'current', 'w_ss': 0.8, 'w_as': 0.2, 'version': 9})
        with patch.object(fb, '_collections', return_value=(state, history)):
            d = fb.reset_weights()
        self.assertEqual((d['w_ss'], d['version']), (0.6, 10))
        self.assertEqual(state.update_one.call_args[0][1]['$set']['w_ss'], 0.6)
        h = history.insert_one.call_args[0][0]
        self.assertEqual((h['decision'], h['before']['w_ss'], h['after']['w_ss']), ('reset', 0.8, 0.6))

    def test_write_failure_does_not_raise(self):
        state, history = self._cols({'_id': 'current', 'w_ss': 0.6, 'w_as': 0.4, 'version': 0})
        state.update_one.side_effect = RuntimeError('write failed')
        with patch.object(fb, '_collections', return_value=(state, history)):
            r = fb.record_feedback('hire', 80, 60)
        self.assertTrue(r['updated'])          # the decision itself is still logged by the caller
