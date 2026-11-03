"""Quota-aware Gemini embedding layer (no network: simulated client and clock)."""
import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from django.test import SimpleTestCase

from neurohire import embeddings as E


class FakeClock:
    def __init__(self):
        self.t = 1000.0
        self.slept = []

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.slept.append(round(s, 2))
        self.t += s


class QuotaError(Exception):
    """Shaped like google.genai.errors.ClientError for a 429."""

    def __init__(self, delay='24s', quota_id='EmbedContentInputTokensPerMinutePerUserPerProjectPerModel-FreeTier'):
        self.code = 429
        self.details = {'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED',
                                  'message': f'You exceeded your current quota. Please retry in {delay}.',
                                  'details': [{'@type': 'type.googleapis.com/google.rpc.QuotaFailure',
                                               'violations': [{'quotaId': quota_id}]},
                                              {'@type': 'type.googleapis.com/google.rpc.RetryInfo',
                                               'retryDelay': delay}]}}
        super().__init__(f'429 RESOURCE_EXHAUSTED. {self.details}')


def vec(text):
    v = np.zeros(8)
    for w in text.split():
        v[hash(w) % 8] += 1
    return list(v + 0.01)


class FakeClient:
    def __init__(self, fail=None):
        self.calls = []                 # list of contents sent
        self.fail = fail or {}          # call number -> exception

    @property
    def models(self):
        return self

    def embed_content(self, model, contents, config=None):
        self.calls.append(list(contents))
        exc = self.fail.get(len(self.calls))
        if exc:
            raise exc
        return SimpleNamespace(embeddings=[SimpleNamespace(values=vec(t)) for t in contents])


def run(texts, client, clock, limiter=None, cache=None, **kw):
    limiter = limiter or E.TokenRateLimiter(1000, 100, clock=clock)
    return E.embed_texts(texts, client=client, model='m', task_type='T', key_fn=lambda t: 'k:' + t,
                         cache=cache, limiter=limiter, sleep=clock.sleep, stats=E.Stats(), **kw)


class ErrorParsingTests(SimpleTestCase):
    def test_retry_delay_from_retryinfo_and_message(self):
        self.assertEqual(E.retry_delay_seconds(QuotaError('52s')), 52.0)
        self.assertEqual(E.retry_delay_seconds(RuntimeError('quota. Please retry in 24.39s.')), 24.39)
        self.assertIsNone(E.retry_delay_seconds(RuntimeError('boom')))

    def test_classification(self):
        self.assertEqual(E.classify_error(QuotaError()), 'rate')
        self.assertEqual(E.classify_error(QuotaError(quota_id='EmbedContentRequestsPerDayPerProjectPerModel-FreeTier')),
                         'daily')
        self.assertEqual(E.classify_error(RuntimeError('503 UNAVAILABLE')), 'transient')
        self.assertEqual(E.classify_error(RuntimeError('400 INVALID_ARGUMENT')), 'fatal')


class LimiterTests(SimpleTestCase):
    def test_tokens_per_minute_window(self):
        clock = FakeClock()
        lim = E.TokenRateLimiter(1000, 100, clock=clock)
        self.assertEqual(lim.acquire(600, sleep=clock.sleep), 0)
        clock.t += 10
        # 600 + 600 > 1000: wait until the first request leaves the 60 s window (50 s more)
        self.assertAlmostEqual(lim.acquire(600, sleep=clock.sleep), 50.0)

    def test_requests_per_minute(self):
        clock = FakeClock()
        lim = E.TokenRateLimiter(10 ** 9, 2, clock=clock)
        lim.acquire(1, sleep=clock.sleep)
        lim.acquire(1, sleep=clock.sleep)
        self.assertAlmostEqual(lim.acquire(1, sleep=clock.sleep), 60.0)

    def test_penalize_blocks_for_server_delay(self):
        clock = FakeClock()
        lim = E.TokenRateLimiter(1000, 100, clock=clock)
        lim.penalize(24)
        self.assertAlmostEqual(lim.acquire(10, sleep=clock.sleep), 24.0)

    def test_batches_are_token_bounded(self):
        texts = ['x' * 300] * 7            # ~100 tokens each at 3 chars/token
        batches = E.pack_batches(texts, max_items=50, max_tokens=250)
        self.assertEqual([len(b) for b in batches], [2, 2, 2, 1])
        self.assertEqual(sum(batches, []), list(range(7)))


class EmbedTextsTests(SimpleTestCase):
    def test_429_waits_server_delay_and_resends_only_failed_request(self):
        clock = FakeClock()
        texts = [f'resume {i} ' + 'w ' * 150 for i in range(6)]
        client = FakeClient(fail={2: QuotaError('24s')})
        with patch('neurohire.embeddings.random.uniform', return_value=1.0):
            out = run(texts, client, clock, max_tokens=250)
        self.assertEqual(len(out), 6)
        sent = [len(c) for c in client.calls]
        self.assertEqual(sent, [2, 2, 2, 2])                # 3 batches + 1 retry of batch 2 only
        self.assertEqual(client.calls[1], client.calls[2])  # the retry re-sends the same batch
        self.assertIn(25.0, clock.slept)                    # 24 s from the server + 1 s jitter

    def test_cache_skips_texts_already_embedded(self):
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as d:
            cache = E.EmbeddingCache(os.path.join(d, 'c.sqlite'))
            first = run(['a b', 'c d'], FakeClient(), clock, cache=cache)
            client = FakeClient()
            again = run(['a b', 'c d', 'e f'], client, clock, cache=E.EmbeddingCache(os.path.join(d, 'c.sqlite')))
        self.assertEqual(client.calls, [['e f']])
        np.testing.assert_array_equal(again[0], first[0])

    def test_cache_closes_every_connection(self):
        """Open SQLite handles lock the file on Windows (WinError 32 on cleanup)."""
        import sqlite3
        opened = []
        real_connect = sqlite3.connect

        def tracking_connect(*a, **k):
            conn = real_connect(*a, **k)
            opened.append(conn)
            return conn
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'c.sqlite')
            with patch('neurohire.embeddings.sqlite3.connect', side_effect=tracking_connect):
                cache = E.EmbeddingCache(path)
                cache.put_many({'k': np.ones(3)})
                cache.get_many(['k', 'missing'])
                len(cache)
                with self.assertRaises(ValueError):          # a failed write still closes
                    with cache._conn() as c:
                        raise ValueError('boom')
            self.assertEqual(len(opened), 5)
            for conn in opened:
                with self.assertRaises(sqlite3.ProgrammingError):   # "Cannot operate on a closed database"
                    conn.execute('SELECT 1')
            os.remove(path)                                  # file is free to delete

    def test_progress_kept_when_a_later_request_fails(self):
        clock = FakeClock()
        texts = [f't{i} ' + 'w ' * 150 for i in range(4)]
        with tempfile.TemporaryDirectory() as d:
            cache = E.EmbeddingCache(os.path.join(d, 'c.sqlite'))
            client = FakeClient(fail={2: RuntimeError('400 INVALID_ARGUMENT')})
            with self.assertRaises(E.EmbeddingError):
                run(texts, client, clock, cache=cache, max_tokens=250)
            self.assertEqual(len(cache), 2)                 # first request's vectors survived
            client2 = FakeClient()
            run(texts, client2, clock, cache=cache, max_tokens=250)
            self.assertEqual(client2.calls, [texts[2:]])     # resumes where it stopped

    def test_daily_quota_stops_immediately(self):
        clock = FakeClock()
        client = FakeClient(fail={1: QuotaError(quota_id='EmbedContentRequestsPerDayPerProjectPerModel')})
        with self.assertRaises(E.DailyQuotaExhausted):
            run(['a'], client, clock)
        self.assertEqual(len(client.calls), 1)

    def test_gives_up_after_max_retries(self):
        clock = FakeClock()
        client = FakeClient(fail={i: QuotaError('5s') for i in range(1, 10)})
        with self.assertRaisesRegex(E.EmbeddingError, 'gave up after 3 attempts'):
            run(['a'], client, clock, max_retries=3)
        self.assertEqual(len(client.calls), 3)

    def test_bounded_wait_for_app_requests(self):
        clock = FakeClock()
        client = FakeClient(fail={1: QuotaError('52s')})
        with self.assertRaisesRegex(E.EmbeddingError, 'not waiting'):
            run(['a'], client, clock, max_total_wait=20)
        self.assertEqual(len(client.calls), 1)

    def test_duplicates_sent_once(self):
        clock = FakeClock()
        client = FakeClient()
        out = run(['same', 'same', 'other'], client, clock)
        self.assertEqual(client.calls, [['same', 'other']])
        np.testing.assert_array_equal(out[0], out[1])


class StrictSimilarityTests(SimpleTestCase):
    def setUp(self):
        E.reset_shared_limiter()
        self.addCleanup(E.reset_shared_limiter)

    def test_strict_raises_instead_of_tfidf(self):
        from neurohire import analysis_engine as ae
        client = FakeClient(fail={1: RuntimeError('400 INVALID_ARGUMENT')})
        with patch.object(ae, '_get_gemini_client', return_value=client):
            with self.assertRaises(E.EmbeddingError):
                ae.get_similarity_batch(['react dev'], 'react role', strict=True)
            # The app (non-strict) still falls back, and labels it honestly.
            client.fail = {2: RuntimeError('400 INVALID_ARGUMENT')}
            self.assertEqual(ae.get_similarity_batch(['react dev'], 'react role')['method'], 'tfidf')

    def test_strict_without_client_raises(self):
        from neurohire import analysis_engine as ae
        with patch.object(ae, '_get_gemini_client', return_value=None):
            with self.assertRaises(E.EmbeddingError):
                ae.get_similarity_batch(['react dev'], 'react role', strict=True)
