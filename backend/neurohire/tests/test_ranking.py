"""
Task 3 tests — ranking against a job description, persistence, deduplication.

Run:  python manage.py test neurohire.test_ranking
"""
import json
from unittest.mock import MagicMock, patch

import numpy as np
from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings

from neurohire.models import UserProfile
from neurohire.ranking import rank_candidates

TRUSTED = 'https://neurohire-bay.vercel.app'


def fake_similarity(scores, method='gemini'):
    def fn(texts, jd, caches):
        return {'scores': list(scores), 'cosines': [None] * len(texts), 'method': method,
                'new_embeddings': [None] * len(texts)}
    return fn


def cand(i, name, cs=100.0, vs=50.0, lv=None, skills=()):
    return {'id': f'id{i}', 'name': name, 'text': f'resume {i}', 'skills': list(skills),
            'consistency_score': cs, 'skill_validation_score': vs, 'lv_raw': lv}


class RankCandidatesTests(SimpleTestCase):

    def test_orders_by_final_score(self):
        cands = [cand(1, 'A', cs=100, vs=0), cand(2, 'B', cs=100, vs=100), cand(3, 'C', cs=53, vs=0)]
        out = rank_candidates(cands, 'react developer', fake_similarity([60, 60, 90]), vs_variant='original')
        names = [r['name'] for r in out['results']]
        # FS: A = .6*60+.4*50 = 56, B = .6*60+.4*100 = 76, C = .6*90+.4*26.5 = 64.6
        self.assertEqual(names, ['B', 'C', 'A'])
        self.assertEqual([r['rank'] for r in out['results']], [1, 2, 3])

    def test_ties_broken_by_ss_then_name(self):
        cands = [cand(1, 'Zed'), cand(2, 'amy'), cand(3, 'Bob')]
        out = rank_candidates(cands, 'jd text here', fake_similarity([50, 50, 50]), vs_variant='original')
        self.assertEqual([r['name'] for r in out['results']], ['amy', 'Bob', 'Zed'])

    def test_lv_normalised_over_the_ranked_set(self):
        cands = [cand(1, 'A', lv=0.5), cand(2, 'B', lv=1.5), cand(3, 'C', lv=1.0), cand(4, 'D', lv=None)]
        out = rank_candidates(cands, 'jd', fake_similarity([50, 50, 50, 50]), vs_variant='original')
        lv = {r['name']: r['lv_score'] for r in out['results']}
        self.assertEqual(lv, {'A': 0.0, 'B': 100.0, 'C': 50.0, 'D': None})
        self.assertEqual(out['lv_bounds'], {'min': 0.5, 'max': 1.5, 'n_with_lv': 3})
        d = next(r for r in out['results'] if r['name'] == 'D')
        self.assertIn('LV', d['missing_components'])

    def test_ablation_components(self):
        c = [cand(1, 'A', cs=100, vs=0, lv=1.0)]
        ss_only = rank_candidates(c, 'jd', fake_similarity([70]), components={'SS'}, vs_variant='original')['results'][0]
        self.assertEqual(ss_only['final_score'], 70.0)
        ss_cs = rank_candidates(c, 'jd', fake_similarity([70]), components={'SS', 'CS'}, vs_variant='original')['results'][0]
        self.assertEqual(ss_cs['final_score'], round(0.6 * 70 + 0.4 * 100, 2))
        full = rank_candidates(c, 'jd', fake_similarity([70]), vs_variant='original')['results'][0]
        # single candidate: min == max → LV 0.5 → 50
        self.assertEqual(full['lv_score'], 50.0)
        self.assertEqual(full['analytical_score'], 50.0)

    def test_matched_and_missing_skills(self):
        c = [cand(1, 'A', skills=['react', 'jest'])]
        out = rank_candidates(c, 'React, TypeScript and Jest', fake_similarity([50]),
                              extract_skills_fn=lambda t: ['jest', 'react', 'typescript'], vs_variant='original')
        r = out['results'][0]
        self.assertEqual(r['matched_skills'], ['jest', 'react'])
        self.assertEqual(r['missing_skills'], ['typescript'])

    def test_unscorable_similarity_falls_back_to_as(self):
        out = rank_candidates([cand(1, 'A', cs=80, vs=40)], 'jd', fake_similarity([None], 'none'), vs_variant='original')
        r = out['results'][0]
        self.assertIsNone(r['semantic_score'])
        self.assertEqual(r['final_score'], 60.0)
        self.assertIn('SS', r['missing_components'])


class SimilarityBatchTests(SimpleTestCase):

    def _client(self):
        client = MagicMock()

        def embed(model, contents, config=None):
            vecs = []
            for t in contents:
                v = np.zeros(3)
                v[0] = 1.0
                v[1] = 1.0 if 'react' in t else 0.0
                vecs.append(MagicMock(values=list(v)))
            return MagicMock(embeddings=vecs)
        client.models.embed_content.side_effect = embed
        return client

    def test_batch_scores_and_cache_reuse(self):
        from neurohire import analysis_engine as ae
        client = self._client()
        with patch.object(ae, '_get_gemini_client', return_value=client):
            first = ae.get_similarity_batch(['react dev', 'java dev'], 'react role')
            self.assertEqual(first['method'], 'gemini')
            self.assertEqual(client.models.embed_content.call_count, 1)        # JD + 2 résumés, one call
            self.assertGreater(first['scores'][0], first['scores'][1])
            caches = first['new_embeddings']
            self.assertTrue(all(c and c['key'] for c in caches))

            client.models.embed_content.reset_mock()
            second = ae.get_similarity_batch(['react dev', 'java dev'], 'react role', caches)
            sent = client.models.embed_content.call_args.kwargs['contents']
            self.assertEqual(sent, ['react role'])                               # only the JD
            self.assertEqual(second['scores'], first['scores'])
            self.assertEqual(second['new_embeddings'], [None, None])

    def test_stale_cache_is_ignored(self):
        from neurohire import analysis_engine as ae
        client = self._client()
        with patch.object(ae, '_get_gemini_client', return_value=client):
            out = ae.get_similarity_batch(['react dev'], 'react role', [{'key': 'old', 'values': [0, 0, 1]}])
        self.assertEqual(client.models.embed_content.call_args.kwargs['contents'], ['react role', 'react dev'])
        self.assertIsNotNone(out['new_embeddings'][0])

    def test_large_batches_are_chunked(self):
        from neurohire import analysis_engine as ae
        client = self._client()
        with patch.object(ae, '_get_gemini_client', return_value=client), patch.object(ae, 'EMBED_BATCH_SIZE', 4):
            out = ae.get_similarity_batch([f'react {i}' for i in range(9)], 'react role')
        self.assertEqual(client.models.embed_content.call_count, 3)              # 10 texts / 4
        self.assertTrue(all(s is not None for s in out['scores']))

    def test_any_failure_falls_back_to_tfidf_for_all(self):
        from neurohire import analysis_engine as ae
        client = MagicMock()
        client.models.embed_content.side_effect = RuntimeError('quota')
        with patch.object(ae, '_get_gemini_client', return_value=client):
            out = ae.get_similarity_batch(['react typescript', 'cobol'], 'react typescript role')
        self.assertEqual(out['method'], 'tfidf')
        self.assertGreater(out['scores'][0], out['scores'][1])

    def test_empty_jd(self):
        from neurohire import analysis_engine as ae
        out = ae.get_similarity_batch(['a'], '  ')
        self.assertEqual(out['scores'], [None])
        self.assertEqual(out['method'], 'none')


class DeduplicationTests(SimpleTestCase):

    @patch('neurohire.mongo_client.candidates_collection')
    def test_email_lowercased_and_sources_recorded(self, cc):
        from neurohire.mongo_client import mongo_insert_candidate
        col = MagicMock()
        col.find_one.return_value = None
        col.insert_one.return_value = MagicMock(inserted_id='x1')
        cc.return_value = col
        mongo_insert_candidate({'email': ' Asha@Example.COM ', 'source': 'resume_upload'})
        col.find_one.assert_called_once_with({'email': 'asha@example.com'})
        doc = col.insert_one.call_args[0][0]
        self.assertEqual(doc['email'], 'asha@example.com')
        self.assertEqual(doc['sources'], ['resume_upload'])

    @patch('neurohire.mongo_client.candidates_collection')
    def test_merge_keeps_created_at_and_accumulates_sources(self, cc):
        from bson import ObjectId
        from neurohire.mongo_client import mongo_insert_candidate
        col = MagicMock()
        col.find_one.return_value = {'_id': ObjectId(), 'email': 'a@b.com', 'skills': ['React'],
                                     'source': 'github_search', 'created_at': 'old'}
        cc.return_value = col
        mongo_insert_candidate({'email': 'a@b.com', 'skills': ['react', 'jest'], 'source': 'resume_upload',
                                'final_score': 70, 'created_at': 'new'})
        upd = col.update_one.call_args[0][1]['$set']
        self.assertEqual(upd['skills'], ['React', 'jest'])           # case-insensitive union
        self.assertEqual(upd['sources'], ['github_search', 'resume_upload'])
        self.assertNotIn('created_at', upd)
        self.assertEqual(upd['final_score'], 70)

    @patch('neurohire.mongo_client.candidates_collection')
    def test_no_email_always_inserts(self, cc):
        from neurohire.mongo_client import mongo_insert_candidate
        col = MagicMock()
        col.insert_one.return_value = MagicMock(inserted_id='x2')
        cc.return_value = col
        mongo_insert_candidate({'name': 'GitHub user', 'source': 'github_search'})
        col.find_one.assert_not_called()
        col.insert_one.assert_called_once()

    @patch('neurohire.mongo_client.candidates_collection')
    def test_list_hides_internal_fields(self, cc):
        from neurohire.mongo_client import mongo_all_candidates
        col = MagicMock()
        col.find.return_value.sort.return_value.limit.return_value = []
        cc.return_value = col
        mongo_all_candidates()
        projection = col.find.call_args[0][1]
        self.assertEqual(projection, {'resume_text_redacted': 0, 'embedding_cache': 0})


@override_settings(CORS_ALLOWED_ORIGINS=[TRUSTED])
class RankEndpointTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.client = Client(enforce_csrf_checks=True)
        self.rec = User.objects.create_user('rec@company.com', 'rec@company.com', 'pw-12345678')
        UserProfile.objects.create(user=self.rec, role='recruiter')
        self.seek = User.objects.create_user('s@example.com', 's@example.com', 'pw-12345678')
        UserProfile.objects.create(user=self.seek, role='jobseeker')
        self.docs = [
            {'id': 'a1', 'name': 'Asha', 'email': 'asha@x.com', 'resume_text_redacted': 'react typescript jest',
             'skills': ['react', 'typescript', 'jest'], 'consistency_score': 100.0,
             'skill_validation_score': 80.0, 'lv_raw': 1.0, 'embedding_cache': None},
            {'id': 'b2', 'name': 'Ben', 'email': 'ben@x.com', 'resume_text_redacted': 'java spring oracle',
             'skills': ['java'], 'consistency_score': 100.0, 'skill_validation_score': 20.0,
             'lv_raw': 0.2, 'embedding_cache': None},
        ]

    def _post(self, body):
        return self.client.post('/api/rank/', json.dumps(body), content_type='application/json',
                                HTTP_ORIGIN=TRUSTED)

    JD = 'Senior Frontend Developer with React, TypeScript and Jest experience'

    def test_requires_recruiter(self):
        self.assertEqual(self._post({'job_description': self.JD}).status_code, 403)
        self.client.force_login(self.seek)
        self.assertEqual(self._post({'job_description': self.JD}).status_code, 403)

    def test_validation(self):
        self.client.force_login(self.rec)
        self.assertEqual(self._post({'job_description': 'short'}).status_code, 400)
        self.assertEqual(self._post({'job_description': self.JD, 'components': ['CS']}).status_code, 400)
        self.assertEqual(self._post({'job_description': self.JD, 'components': ['SS', 'XX']}).status_code, 400)
        self.assertEqual(self._post({'job_description': self.JD, 'candidate_ids': 'a1'}).status_code, 400)

    @patch('neurohire.views.mongo_save_ranking', return_value='rk1')
    @patch('neurohire.views.mongo_set_embedding_cache')
    @patch('neurohire.views.mongo_is_available', return_value=True)
    def test_ranks_and_stores_run(self, _avail, set_cache, save):
        with patch('neurohire.views.mongo_candidates_for_ranking', return_value=[dict(d) for d in self.docs]):
            self.client.force_login(self.rec)
            resp = self._post({'job_description': self.JD})
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body['ranking_id'], 'rk1')
        self.assertEqual([r['name'] for r in body['results']], ['Asha', 'Ben'])
        top = body['results'][0]
        for key in ('semantic_score', 'consistency_score', 'skill_validation_score', 'lv_score',
                    'analytical_score', 'final_score', 'final_fit', 'rank', 'missing_components'):
            self.assertIn(key, top)
        self.assertEqual(top['lv_score'], 100.0)                 # normalised over the two
        self.assertNotIn('resume_text_redacted', json.dumps(body))
        self.assertNotIn('embedding_cache', json.dumps(body))
        saved = save.call_args[0][0]
        self.assertEqual(saved['job_description'], self.JD)
        self.assertEqual(len(saved['results']), 2)

    @patch('neurohire.views.mongo_is_available', return_value=True)
    @patch('neurohire.views.mongo_candidates_for_ranking', return_value=[])
    def test_nothing_to_rank(self, _c, _a):
        self.client.force_login(self.rec)
        resp = self._post({'job_description': self.JD})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['results'], [])

    @patch('neurohire.views.mongo_save_ranking', return_value='rk1')
    @patch('neurohire.views.mongo_set_embedding_cache')
    @patch('neurohire.views.mongo_is_available', return_value=True)
    def test_top_k(self, *_):
        with patch('neurohire.views.mongo_candidates_for_ranking', return_value=[dict(d) for d in self.docs]):
            self.client.force_login(self.rec)
            body = self._post({'job_description': self.JD, 'top_k': 1}).json()
        self.assertEqual(len(body['results']), 1)
        self.assertEqual(body['total_ranked'], 2)


@override_settings(CORS_ALLOWED_ORIGINS=[TRUSTED])
class UploadStorageTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.rec = User.objects.create_user('rec@company.com', 'rec@company.com', 'pw-12345678')
        UserProfile.objects.create(user=self.rec, role='recruiter')

    @patch('neurohire.views.mongo_insert_candidate', return_value='c1')
    @patch('neurohire.views.analyze_resume', return_value={
        'name': 'A', 'skills': ['react'], 'final_score': 70, 'semantic_score': 60,
        'resume_text_redacted': 'react developer', 'embedding_cache': {'key': 'k', 'values': [1.0]}})
    def test_internal_fields_stored_not_returned(self, _an, ins):
        from django.core.files.uploadedfile import SimpleUploadedFile
        c = Client()
        c.force_login(self.rec)
        resp = c.post('/api/upload-resume/', {'resume': SimpleUploadedFile('cv.pdf', b'%PDF')}, HTTP_ORIGIN=TRUSTED)
        self.assertEqual(resp.status_code, 201, resp.content)
        stored = ins.call_args[0][0]
        self.assertEqual(stored['resume_text_redacted'], 'react developer')
        self.assertEqual(stored['final_score'], 70)
        self.assertNotIn('resume_text_redacted', resp.json()['analysis'])
        self.assertNotIn('embedding_cache', resp.json()['analysis'])


@override_settings(CORS_ALLOWED_ORIGINS=[TRUSTED])
class ChatbotRoleTests(TestCase):

    @patch('neurohire.mongo_client._get_db', return_value=None)
    @patch('neurohire.views._chatbot_reply', return_value=('ok', 'general'))
    def test_browser_cannot_claim_recruiter(self, reply, _db):
        resp = Client().post('/api/chatbot/', json.dumps({'message': 'show top candidates', 'role': 'recruiter'}),
                             content_type='application/json', HTTP_ORIGIN=TRUSTED)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(reply.call_args[0][3], 'jobseeker')

    @patch('neurohire.mongo_client._get_db', return_value=None)
    @patch('neurohire.views._chatbot_reply', return_value=('ok', 'general'))
    def test_verified_recruiter_gets_recruiter_answers(self, reply, _db):
        User = get_user_model()
        u = User.objects.create_user('rec@company.com', 'rec@company.com', 'pw-12345678')
        UserProfile.objects.create(user=u, role='recruiter')
        c = Client()
        c.force_login(u)
        c.post('/api/chatbot/', json.dumps({'message': 'show top candidates'}),
               content_type='application/json', HTTP_ORIGIN=TRUSTED)
        self.assertEqual(reply.call_args[0][3], 'recruiter')


@override_settings(CORS_ALLOWED_ORIGINS=[TRUSTED])
class CandidateStatusTests(TestCase):
    """PATCH /api/candidates/<id>/ used by the schedule modal (Task 5)."""

    def setUp(self):
        User = get_user_model()
        self.rec = User.objects.create_user('rec@company.com', 'rec@company.com', 'pw-12345678')
        UserProfile.objects.create(user=self.rec, role='recruiter')
        self.c = Client()
        self.c.force_login(self.rec)

    def _patch(self, body, cid='65f0c0ffee0000000000abcd'):
        return self.c.patch(f'/api/candidates/{cid}/', json.dumps(body), content_type='application/json',
                            HTTP_ORIGIN=TRUSTED)

    @patch('neurohire.views.mongo_update_candidate_status', return_value=True)
    def test_status_update(self, upd):
        resp = self._patch({'status': 'scheduled'})
        self.assertEqual(resp.status_code, 200, resp.content)
        upd.assert_called_once_with('65f0c0ffee0000000000abcd', 'scheduled')

    @patch('neurohire.views.mongo_update_candidate_status', return_value=False)
    def test_unknown_candidate(self, _upd):
        self.assertEqual(self._patch({'status': 'scheduled'}).status_code, 404)

    @patch('neurohire.views.mongo_update_candidate_status')
    def test_only_known_statuses(self, upd):
        self.assertEqual(self._patch({'status': 'deleted'}).status_code, 400)
        self.assertEqual(self._patch({'final_score': 100}).status_code, 400)
        upd.assert_not_called()

    def test_recruiter_only(self):
        resp = Client().patch('/api/candidates/x/', json.dumps({'status': 'scheduled'}),
                              content_type='application/json', HTTP_ORIGIN=TRUSTED)
        self.assertEqual(resp.status_code, 403)



class RevisedVSRankingTests(SimpleTestCase):
    """Default VS = evidence for THIS job description's skills."""

    def _c(self, i, name, evidenced):
        return {'id': f'id{i}', 'name': name, 'text': 't', 'skills': ['react', 'java'],
                'consistency_score': 100.0, 'skill_validation_score': 99.0, 'lv_raw': None,
                'skill_validation_score_original': 10.0,
                'validated_skills_evidence': [{'skill': s, 'status': 'Valid'} for s in evidenced]}

    def test_vs_recomputed_for_each_jd(self):
        cands = [self._c(1, 'React person', ['react']), self._c(2, 'Java person', ['java'])]
        skills = lambda t: ['react'] if 'React' in t else ['java']
        react = rank_candidates(cands, 'React role', fake_similarity([50, 50]), skills)
        java = rank_candidates(cands, 'Java role', fake_similarity([50, 50]), skills)
        self.assertEqual(react['results'][0]['name'], 'React person')
        self.assertEqual(java['results'][0]['name'], 'Java person')
        self.assertEqual(react['vs_variant'], 'jd')
        self.assertEqual(react['results'][0]['skill_validation_score'], 100.0)

    def test_original_variant_uses_stored_original_vs(self):
        out = rank_candidates([self._c(1, 'A', ['react'])], 'React role', fake_similarity([50]),
                              lambda t: ['react'], vs_variant='paper')          # alias
        self.assertEqual(out['vs_variant'], 'original')
        self.assertEqual(out['results'][0]['skill_validation_score'], 10.0)
