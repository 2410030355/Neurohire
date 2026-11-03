"""
Gemini embedding calls that respect the API's quotas.

  * Token-aware rate limiting: a sliding 60-second window of the tokens and
    requests already sent; a request waits until it fits (GEMINI_EMBED_TPM,
    GEMINI_EMBED_RPM, with a safety margin).
  * Token-bounded batches: texts are packed into requests of at most
    GEMINI_EMBED_MAX_REQUEST_TOKENS estimated tokens (and EMBED_BATCH_SIZE texts),
    sent sequentially.
  * HTTP 429: the server's retry delay (RetryInfo.retryDelay / "retry in Ns") is
    honoured and only the failed request is retried; batches that already
    succeeded are never re-sent. A per-day quota error stops at once.
  * Caching: every successful vector is stored (optional SQLite file), so an
    interrupted run resumes without re-embedding.

Nothing here falls back to another representation: failures raise
EmbeddingError and the caller decides (the app falls back to TF-IDF and labels
it 'tfidf'; the evaluation stops).
"""
from __future__ import annotations

import json
import logging
import math
import os
import random
import re
import sqlite3
import threading
import time
from contextlib import contextmanager
from collections import deque
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np

logger = logging.getLogger('neurohire.embeddings')


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, '') or default)
    except ValueError:
        return default


# Free tier for gemini-embedding-001 (Nov 2026): 30,000 input tokens and 100 requests per minute.
TPM_LIMIT = _env_float('GEMINI_EMBED_TPM', 30000)
RPM_LIMIT = _env_float('GEMINI_EMBED_RPM', 100)
SAFETY = _env_float('GEMINI_EMBED_SAFETY', 0.85)          # use 85 % of the quota
# Conservative estimate (English is ~4 chars/token; résumés with symbols are denser).
CHARS_PER_TOKEN = _env_float('GEMINI_CHARS_PER_TOKEN', 3.0)
MAX_RETRIES = int(_env_float('GEMINI_EMBED_MAX_RETRIES', 8))
BACKOFF_SECONDS = _env_float('GEMINI_EMBED_BACKOFF', 5.0)  # when the server gives no delay
MAX_BACKOFF_SECONDS = 120.0


class EmbeddingError(RuntimeError):
    """Embeddings could not be obtained (after retries, or a non-retryable error)."""


class DailyQuotaExhausted(EmbeddingError):
    """The per-day quota is used up; retrying today will not help."""


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text or '') / CHARS_PER_TOKEN))


# ── Errors ──────────────────────────────────────────────────────────────────

_RETRY_IN = re.compile(r'retry in\s+([\d.]+)\s*s', re.I)
_RETRY_DELAY = re.compile(r"retryDelay['\"]?\s*[:=]\s*['\"]?([\d.]+)s", re.I)


def retry_delay_seconds(exc: BaseException) -> Optional[float]:
    """The delay the server asked for, from RetryInfo or the message; None if absent."""
    details = getattr(exc, 'details', None)
    if isinstance(details, dict):
        for d in (details.get('error', details).get('details') or []):
            if isinstance(d, dict) and d.get('retryDelay'):
                m = re.match(r'([\d.]+)s', str(d['retryDelay']))
                if m:
                    return float(m.group(1))
    text = str(exc)
    for pattern in (_RETRY_DELAY, _RETRY_IN):
        m = pattern.search(text)
        if m:
            return float(m.group(1))
    return None


def classify_error(exc: BaseException) -> str:
    """'daily' | 'rate' | 'transient' | 'fatal'."""
    text = str(exc)
    code = getattr(exc, 'code', None)
    if code is None:
        m = re.match(r'\s*(\d{3})\b', text)
        code = int(m.group(1)) if m else None
    rate = code == 429 or 'RESOURCE_EXHAUSTED' in text or re.search(r'\b429\b', text)
    if rate and re.search(r'PerDay|per day|daily', text, re.I):
        return 'daily'
    if rate:
        return 'rate'
    if code in (500, 502, 503, 504) or re.search(r'UNAVAILABLE|DEADLINE_EXCEEDED|timed? ?out|Connection', text, re.I):
        return 'transient'
    return 'fatal'


# ── Rate limiter ────────────────────────────────────────────────────────────

class TokenRateLimiter:
    """
    Sliding-window limiter for tokens and requests per minute. acquire()
    sleeps exactly as long as needed for the request to fit, then records it.
    Thread-safe: requests are admitted one at a time.
    """

    def __init__(self, tokens_per_minute: float, requests_per_minute: float, window: float = 60.0,
                 clock: Callable[[], float] = time.monotonic):
        self.tpm, self.rpm, self.window, self.clock = tokens_per_minute, requests_per_minute, window, clock
        self.initial_tpm = tokens_per_minute
        self.events: deque = deque()          # (time, tokens)
        self.blocked_until = 0.0
        self.lock = threading.Lock()

    def _prune(self, now: float):
        while self.events and self.events[0][0] <= now - self.window:
            self.events.popleft()

    def wait_time(self, tokens: int, now: Optional[float] = None) -> float:
        now = self.clock() if now is None else now
        self._prune(now)
        wait = max(0.0, self.blocked_until - now)
        used = sum(t for _, t in self.events)
        # Tokens: wait until enough old requests leave the window. A request larger
        # than the whole budget is admitted once the window is empty.
        need = used + tokens - self.tpm
        if need > 0:
            freed = 0
            for ts, t in self.events:
                freed += t
                if freed >= need:
                    wait = max(wait, ts + self.window - now)
                    break
        if len(self.events) + 1 > self.rpm:
            ts = self.events[len(self.events) - int(self.rpm)][0]
            wait = max(wait, ts + self.window - now)
        return wait

    def acquire(self, tokens: int, sleep: Callable[[float], None] = time.sleep,
                on_wait: Optional[Callable[[float, int], None]] = None) -> float:
        with self.lock:
            wait = self.wait_time(tokens)
            if wait > 0:
                if on_wait:
                    on_wait(wait, tokens)
                sleep(wait)
            now = self.clock()
            self.blocked_until = 0.0
            self.events.append((now, tokens))
            return wait

    def penalize(self, seconds: float, adapt: bool = True):
        """
        After a 429: nothing is sent before `seconds` (the server's delay) have
        passed. If our token estimate was too low (the server counted more),
        the per-minute budget is lowered by 15 % (never below 30 % of the start).
        """
        with self.lock:
            self.blocked_until = max(self.blocked_until, self.clock() + seconds)
            if adapt:
                floor = 0.3 * self.initial_tpm
                if self.tpm > floor:
                    self.tpm = max(floor, self.tpm * 0.85)
                    logger.info('Gemini rate limit: lowering pacing to %.0f tokens/min.', self.tpm)


_shared_limiter: Optional[TokenRateLimiter] = None
_shared_lock = threading.Lock()


def shared_limiter() -> TokenRateLimiter:
    """One limiter per process: the quota is per API key/project, not per call site."""
    global _shared_limiter
    with _shared_lock:
        if _shared_limiter is None:
            _shared_limiter = TokenRateLimiter(TPM_LIMIT * SAFETY, max(1, math.floor(RPM_LIMIT * SAFETY)))
        return _shared_limiter


def reset_shared_limiter(limiter: Optional[TokenRateLimiter] = None):
    global _shared_limiter
    with _shared_lock:
        _shared_limiter = limiter


def max_request_tokens() -> int:
    """Largest request: half the effective per-minute budget, so pacing stays smooth
    and a retried request wastes little quota."""
    default = TPM_LIMIT * SAFETY / 2
    return int(_env_float('GEMINI_EMBED_MAX_REQUEST_TOKENS', default))


# ── Cache ───────────────────────────────────────────────────────────────────

class EmbeddingCache:
    """SQLite store: key (model|task|text hash) → float64 vector. Safe to reuse across runs."""

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._lock = threading.Lock()
        with self._conn() as c:
            c.execute('CREATE TABLE IF NOT EXISTS emb (key TEXT PRIMARY KEY, dim INTEGER, vec BLOB)')

    @contextmanager
    def _conn(self):
        """
        Open, run one transaction, and CLOSE. (A sqlite3.Connection used as a
        context manager only commits/rolls back; it stays open and keeps the
        file locked on Windows, so the file could not be deleted or moved.)
        """
        conn = sqlite3.connect(self.path, timeout=30)
        try:
            with conn:                 # commit on success, roll back on error
                yield conn
        finally:
            conn.close()

    def get_many(self, keys: Sequence[str]) -> Dict[str, np.ndarray]:
        out = {}
        keys = list(dict.fromkeys(keys))
        with self._lock, self._conn() as c:
            for i in range(0, len(keys), 500):
                part = keys[i:i + 500]
                q = f"SELECT key, vec FROM emb WHERE key IN ({','.join('?' * len(part))})"
                for k, blob in c.execute(q, part):
                    out[k] = np.frombuffer(blob, dtype=np.float64).copy()
        return out

    def put_many(self, items: Dict[str, np.ndarray]):
        if not items:
            return
        with self._lock, self._conn() as c:
            c.executemany('INSERT OR REPLACE INTO emb (key, dim, vec) VALUES (?, ?, ?)',
                          [(k, len(v), np.asarray(v, dtype=np.float64).tobytes()) for k, v in items.items()])

    def __len__(self):
        with self._conn() as c:
            return c.execute('SELECT COUNT(*) FROM emb').fetchone()[0]


# ── Embedder ────────────────────────────────────────────────────────────────

class Stats:
    def __init__(self):
        self.requests = self.texts_sent = self.tokens_sent = self.cache_hits = 0
        self.retries = 0
        self.waited_s = 0.0

    def as_dict(self):
        return {'requests': self.requests, 'texts_sent': self.texts_sent, 'est_tokens_sent': self.tokens_sent,
                'cache_hits': self.cache_hits, 'retries': self.retries, 'waited_s': round(self.waited_s, 1)}


STATS = Stats()   # process-wide counters (reported by the evaluate command)


def pack_batches(texts: List[str], max_items: int, max_tokens: int) -> List[List[int]]:
    """Indices of `texts` grouped into requests within both limits (order kept)."""
    batches, cur, cur_tokens = [], [], 0
    for i, t in enumerate(texts):
        n = estimate_tokens(t)
        if cur and (len(cur) >= max_items or cur_tokens + n > max_tokens):
            batches.append(cur)
            cur, cur_tokens = [], 0
        cur.append(i)
        cur_tokens += n
    if cur:
        batches.append(cur)
    return batches


def embed_texts(texts: List[str], *, client, model: str, task_type: str, key_fn: Callable[[str], str],
                cache: Optional[EmbeddingCache] = None, memory: Optional[Dict[str, np.ndarray]] = None,
                limiter: Optional[TokenRateLimiter] = None, max_items: int = 50,
                max_tokens: Optional[int] = None, max_retries: Optional[int] = None,
                max_total_wait: Optional[float] = None, sleep: Callable[[float], None] = time.sleep,
                stats: Stats = STATS) -> List[np.ndarray]:
    """
    One vector per text (same order). Raises EmbeddingError if any text cannot
    be embedded; vectors obtained before the failure stay cached.
    max_total_wait bounds the time spent waiting on quota (the app uses a small
    value so a web request never hangs; the evaluation waits as long as needed).
    """
    if client is None:
        raise EmbeddingError('Gemini client is not configured (GEMINI_API_KEY missing).')
    limiter = limiter or shared_limiter()
    max_tokens = max_tokens or max_request_tokens()
    max_retries = MAX_RETRIES if max_retries is None else max_retries
    keys = [key_fn(t) for t in texts]
    vectors: Dict[str, np.ndarray] = {}
    if memory:
        vectors.update({k: memory[k] for k in keys if k in memory})
    missing = [k for k in dict.fromkeys(keys) if k not in vectors]
    if cache is not None and missing:
        vectors.update(cache.get_many(missing))
    stats.cache_hits += sum(1 for k in dict.fromkeys(keys) if k in vectors)

    todo_keys = [k for k in dict.fromkeys(keys) if k not in vectors]
    first_text = {}
    for k, t in zip(keys, texts):
        first_text.setdefault(k, t)
    todo = [first_text[k] for k in todo_keys]
    batches = pack_batches(todo, max_items, max_tokens)
    waited = 0.0

    def note_wait(seconds, tokens):
        logger.info('Gemini rate limit: waiting %.1fs before sending ~%d tokens (quota %.0f tokens/min).',
                    seconds, tokens, limiter.tpm)

    for b, idx in enumerate(batches, start=1):
        chunk = [todo[i] for i in idx]
        tokens = sum(estimate_tokens(t) for t in chunk)
        attempt = 0
        while True:
            attempt += 1
            waited += limiter.acquire(tokens, sleep=sleep, on_wait=note_wait)
            try:
                kwargs = {'model': model, 'contents': chunk}
                if task_type:
                    kwargs['config'] = {'task_type': task_type}
                response = client.models.embed_content(**kwargs)
                got = _vectors_from(response, len(chunk))
            except EmbeddingError:
                raise
            except Exception as e:
                kind = classify_error(e)
                if kind == 'daily':
                    raise DailyQuotaExhausted(
                        f'Gemini daily quota exhausted ({_short(e)}). {len(vectors)} vectors are cached; '
                        're-run after the quota resets to continue from there.') from e
                if kind == 'fatal' or attempt >= max_retries:
                    what = 'non-retryable error' if kind == 'fatal' else f'gave up after {attempt} attempts'
                    logger.error('Gemini embedding request %d/%d failed (%s): %s', b, len(batches), what, _short(e))
                    raise EmbeddingError(f'Gemini embeddings failed on request {b}/{len(batches)} '
                                         f'({what}): {_short(e)}') from e
                server = retry_delay_seconds(e) if kind == 'rate' else None
                delay = server if server is not None else min(MAX_BACKOFF_SECONDS, BACKOFF_SECONDS * 2 ** (attempt - 1))
                delay += random.uniform(0.5, 1.5)          # jitter
                if max_total_wait is not None and waited + delay > max_total_wait:
                    raise EmbeddingError(f'Gemini rate limited; not waiting {delay:.0f}s '
                                         f'(limit {max_total_wait:.0f}s): {_short(e)}') from e
                logger.warning('Gemini %s on request %d/%d (%d texts, ~%d tokens): retry %d/%d in %.1fs (%s).',
                               'HTTP 429' if kind == 'rate' else 'transient error', b, len(batches), len(chunk),
                               tokens, attempt, max_retries - 1, delay,
                               'server-provided delay' if server is not None else 'back-off')
                stats.retries += 1
                if kind == 'rate':
                    limiter.penalize(delay)
                else:
                    sleep(delay)
                    waited += delay
                continue
            stats.requests += 1
            stats.texts_sent += len(chunk)
            stats.tokens_sent += tokens
            new = {todo_keys[i]: v for i, v in zip(idx, got)}
            vectors.update(new)
            if memory is not None:
                memory.update(new)
            if cache is not None:
                cache.put_many(new)
            if len(batches) > 1:
                logger.info('Gemini embeddings: request %d/%d ok (%d texts, ~%d tokens).',
                            b, len(batches), len(chunk), tokens)
            break
    stats.waited_s += waited
    return [vectors[k] for k in keys]


def _vectors_from(response, n: int) -> List[np.ndarray]:
    embeddings = getattr(response, 'embeddings', None)
    if not embeddings or len(embeddings) != n:
        raise EmbeddingError(f'Malformed Gemini response: expected {n} embeddings, '
                             f'got {len(embeddings) if embeddings else 0}.')
    out = []
    for emb in embeddings:
        values = getattr(emb, 'values', None)
        if not values:
            raise EmbeddingError('Malformed Gemini response: embedding without values.')
        out.append(np.asarray(values, dtype=float))
    return out


def _short(e: BaseException, n: int = 300) -> str:
    s = f'{type(e).__name__}: {e}'
    return s if len(s) <= n else s[:n] + '…'


# ── Process-wide disk cache (enabled by the evaluation) ─────────────────────

_disk_cache: Optional[EmbeddingCache] = None


def set_disk_cache(path: Optional[str]) -> Optional[EmbeddingCache]:
    global _disk_cache
    _disk_cache = EmbeddingCache(path) if path else None
    return _disk_cache


def disk_cache() -> Optional[EmbeddingCache]:
    return _disk_cache


def describe_limits() -> str:
    lim = shared_limiter()
    return (f'Gemini quota pacing: {lim.tpm:.0f} tokens/min, {lim.rpm:.0f} requests/min '
            f'({SAFETY:.0%} of {TPM_LIMIT:.0f} / {RPM_LIMIT:.0f}); ≤{max_request_tokens()} est. tokens per request; '
            f'token estimate = chars / {CHARS_PER_TOKEN:g}.')


def dumps_stats() -> str:
    return json.dumps(STATS.as_dict())
