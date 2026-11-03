"""
Baseline rankers and similarity back-ends for the evaluation.

All scorers take (resume_texts, jd) and return one score per résumé
(higher = better). They are given the SAME redacted text NeuroHire embeds.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Callable, Dict, List, Optional

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_TOKEN = re.compile(r'[a-z0-9][a-z0-9+#.]*[a-z0-9+#]|[a-z0-9]')


def tokenize(text: str) -> List[str]:
    return [t for t in _TOKEN.findall((text or '').lower()) if t not in ENGLISH_STOP_WORDS]


def keyword_skill_overlap(texts: List[str], jd: str) -> List[float]:
    """
    Keyword baseline (typical ATS filter): share of the skills named in the JD
    that also appear in the résumé, using the app's skill catalogue/aliases.
    """
    from neurohire.extraction import extract_skills
    jd_skills = set(extract_skills(jd))
    if not jd_skills:
        return [0.0] * len(texts)
    return [len(jd_skills & set(extract_skills(t))) / len(jd_skills) for t in texts]


def keyword_term_overlap(texts: List[str], jd: str) -> List[float]:
    """Share of distinct JD terms (stop words removed) present in the résumé."""
    q = set(tokenize(jd))
    return [len(q & set(tokenize(t))) / len(q) if q else 0.0 for t in texts]


def bm25(texts: List[str], jd: str, k1: float = 1.5, b: float = 0.75) -> List[float]:
    """Okapi BM25 with the JD as the query and the résumé pool as the corpus."""
    docs = [tokenize(t) for t in texts]
    n = len(docs)
    avgdl = sum(len(d) for d in docs) / n if n else 0
    df = Counter(term for d in docs for term in set(d))
    query = tokenize(jd)
    scores = []
    for d in docs:
        tf = Counter(d)
        s = 0.0
        for term in query:
            if term not in tf:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            s += idf * tf[term] * (k1 + 1) / (tf[term] + k1 * (1 - b + b * len(d) / avgdl))
        scores.append(s)
    return scores


def tfidf_corpus(texts: List[str], jd: str) -> List[float]:
    """TF-IDF fitted on the whole résumé pool + JD, cosine to the JD."""
    vec = TfidfVectorizer(stop_words='english')
    m = vec.fit_transform(list(texts) + [jd])
    return [float(x) for x in cosine_similarity(m[:-1], m[-1]).ravel()]


# ── Similarity back-ends for NeuroHire's SS (same signature as the app) ─────

def tfidf_pair_batch(texts: List[str], jd: str, caches=None) -> Dict:
    """The app's offline fallback: TF-IDF fitted on each résumé/JD pair."""
    from neurohire.analysis_engine import _tfidf_cosine
    from neurohire.scoring import similarity_to_score
    cos = [_tfidf_cosine(t, jd) if t else None for t in texts]
    return {'scores': [None if c is None else similarity_to_score(c) for c in cos],
            'cosines': cos, 'method': 'tfidf', 'new_embeddings': [None] * len(texts)}


GEMINI_RETRIES = None   # attempts per request; None = embeddings.MAX_RETRIES (GEMINI_EMBED_MAX_RETRIES)


def gemini_batch(texts: List[str], jd: str, caches=None, retries: int = None, sleep=None) -> Dict:
    """
    Gemini embeddings via the app's get_similarity_batch in strict mode:
    quota-paced, token-bounded requests sent one after another; an HTTP 429 is
    retried after the server's delay, and only the failed request is re-sent.
    Raises (never falls back to TF-IDF) — a Gemini run must be Gemini for
    every candidate. Successful vectors are kept in the embedding cache, so a
    re-run continues where a failed one stopped.
    """
    from neurohire.analysis_engine import get_similarity_batch
    from neurohire.embeddings import EmbeddingError
    try:
        out = get_similarity_batch(texts, jd, caches, strict=True,
                                   retries=GEMINI_RETRIES if retries is None else retries, sleep=sleep)
    except EmbeddingError as e:
        raise RuntimeError(f'Gemini embeddings unavailable: {e} Nothing was written; vectors obtained so far '
                           'are cached, so re-running continues from there.') from e
    if out['method'] != 'gemini':
        raise RuntimeError(f"Gemini run produced method={out['method']!r}; refusing to label it Gemini.")
    return out


SIMILARITY_BACKENDS: Dict[str, Callable] = {'tfidf': tfidf_pair_batch, 'gemini': gemini_batch}

def baseline_scorers(similarity: str, backend: Optional[Callable] = None
                     ) -> Dict[str, Callable[[List[str], str], List[float]]]:
    """Name → scorer. 'Embedding only' = the chosen similarity back-end alone
    (pass the run's cached back-end so its texts are not embedded twice)."""
    backend = backend or SIMILARITY_BACKENDS[similarity]

    def embedding_only(texts, jd):
        return [s if s is not None else 0.0 for s in backend(texts, jd)['scores']]

    label = 'Gemini embedding only' if similarity == 'gemini' else 'TF-IDF (pairwise) only'
    return {
        'Keyword (skill overlap)': keyword_skill_overlap,
        'Keyword (term overlap)': keyword_term_overlap,
        'BM25': bm25,
        'TF-IDF (corpus)': tfidf_corpus,
        label: embedding_only,
    }
