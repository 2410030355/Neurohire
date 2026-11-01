"""
mongo_client.py
─────────────────────────────────────────────────────────────────────────────
Thin MongoDB access layer for NeuroHire candidate profiles.

Django handles auth, sessions, interviews, waitlist → SQLite/PostgreSQL
MongoDB handles candidate unified profiles             → MongoDB

Usage:
    from .mongo_client import candidates_collection, mongo_insert_candidate,
                               mongo_get_candidate, mongo_all_candidates,
                               mongo_delete_all_candidates
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Connection (lazy, cached) ─────────────────────────────────────────────
_client = None
_db     = None

def _get_db():
    """Return MongoDB database, connecting lazily on first call."""
    global _client, _db
    if _db is not None:
        return _db

    try:
        from pymongo import MongoClient
        from django.conf import settings

        mongo_uri = getattr(settings, 'MONGODB_URI', 'mongodb://localhost:27017/')
        db_name   = getattr(settings, 'MONGODB_DB',  'neurohire')

        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=8000, connectTimeoutMS=8000)
        # Ping to confirm connection
        _client.admin.command('ping')
        _db = _client[db_name]
        logger.info(f"MongoDB connected: {mongo_uri} / {db_name}")
        return _db

    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        return None


def candidates_collection():
    """Return the candidates collection or None if unavailable."""
    db = _get_db()
    if db is None:
        return None
    return db['candidates']


# ── CRUD helpers ──────────────────────────────────────────────────────────

# Fields stored for re-ranking that are never sent to the browser
INTERNAL_FIELDS = ('resume_text_redacted', 'embedding_cache')
_PUBLIC_PROJECTION = {f: 0 for f in INTERNAL_FIELDS}
# List-valued fields that are unioned (not overwritten) when profiles merge
_MERGE_LIST_FIELDS = ('skills', 'companies', 'other_skills')

_email_index_ready = False


def _ensure_email_index(col):
    """Lazy, best-effort index so lookup by e-mail stays fast."""
    global _email_index_ready
    if _email_index_ready:
        return
    try:
        col.create_index('email', sparse=True, background=True)
        _email_index_ready = True
    except Exception as e:
        logger.warning(f"Could not create email index: {e}")


def mongo_insert_candidate(data: dict) -> str | None:
    """
    Insert a candidate profile, or MERGE into the existing profile with the
    same e-mail (paper §III — one unified record per candidate).

    On merge: list fields (skills, companies, other_skills) are unioned, the
    sources the profile came from are accumulated, every other field takes the
    new value (latest analysis wins), created_at is kept.
    Returns the document _id as a string, or None on failure.
    """
    col = candidates_collection()
    if col is None:
        return None
    try:
        now = datetime.utcnow()
        doc = dict(data)
        email = (doc.get('email') or '').strip().lower() or None
        doc['email'] = email
        source = doc.get('source')

        existing = None
        if email:
            _ensure_email_index(col)
            existing = col.find_one({'email': email})

        if existing:
            update = {k: v for k, v in doc.items() if k not in ('_id', 'created_at')}
            for field in _MERGE_LIST_FIELDS:
                old_vals = existing.get(field) or []
                new_vals = doc.get(field) or []
                if old_vals or new_vals:
                    merged, seen = [], set()
                    for v in list(old_vals) + list(new_vals):
                        key = v.lower() if isinstance(v, str) else repr(v)
                        if key not in seen:
                            seen.add(key)
                            merged.append(v)
                    update[field] = merged
            sources = list(existing.get('sources') or ([existing['source']] if existing.get('source') else []))
            if source and source not in sources:
                sources.append(source)
            update['sources'] = sources
            update['updated_at'] = now
            col.update_one({'_id': existing['_id']}, {'$set': update})
            return str(existing['_id'])

        doc['sources'] = [source] if source else []
        doc['created_at'] = now
        doc['updated_at'] = now
        result = col.insert_one(doc)
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"mongo_insert_candidate failed: {e}")
        return None


def mongo_get_candidate(mongo_id: str) -> dict | None:
    """Fetch a single candidate by MongoDB _id string."""
    col = candidates_collection()
    if col is None:
        return None
    try:
        from bson import ObjectId
        doc = col.find_one({'_id': ObjectId(mongo_id)}, _PUBLIC_PROJECTION)
        if doc:
            doc['mongo_id'] = str(doc.pop('_id'))
        return doc
    except Exception as e:
        logger.error(f"mongo_get_candidate failed: {e}")
        return None


def mongo_find_by_github(github_url: str) -> dict | None:
    """Find a candidate by GitHub profile URL."""
    col = candidates_collection()
    if col is None:
        return None
    try:
        doc = col.find_one({'github_url': github_url})
        if doc:
            doc['mongo_id'] = str(doc.pop('_id'))
        return doc
    except Exception as e:
        logger.error(f"mongo_find_by_github failed: {e}")
        return None


def mongo_all_candidates(limit: int = 100) -> list:
    """Return all candidate documents, newest first."""
    col = candidates_collection()
    if col is None:
        return []
    try:
        docs = list(col.find({}, _PUBLIC_PROJECTION).sort('created_at', -1).limit(limit))
        for doc in docs:
            doc['mongo_id'] = str(doc.pop('_id'))
        return docs
    except Exception as e:
        logger.error(f"mongo_all_candidates failed: {e}")
        return []


def mongo_delete_all_candidates() -> int:
    """Delete all candidate documents. Returns deleted count."""
    col = candidates_collection()
    if col is None:
        return 0
    try:
        result = col.delete_many({})
        return result.deleted_count
    except Exception as e:
        logger.error(f"mongo_delete_all_candidates failed: {e}")
        return 0


def mongo_is_available() -> bool:
    """Quick health check — returns True if MongoDB is reachable."""
    return _get_db() is not None

# ── Ranking support ───────────────────────────────────────────────────────

def mongo_candidates_for_ranking(ids: list | None = None, limit: int = 200) -> list:
    """
    Candidates that can be ranked against a JD: they need stored résumé text.
    Returns full documents (including internal fields) with 'id' as a string.
    """
    col = candidates_collection()
    if col is None:
        return []
    try:
        query = {'resume_text_redacted': {'$exists': True, '$nin': [None, '']}}
        if ids:
            from bson import ObjectId
            object_ids = []
            for i in ids:
                try:
                    object_ids.append(ObjectId(str(i)))
                except Exception:
                    continue
            query['_id'] = {'$in': object_ids}
        docs = list(col.find(query).sort('created_at', -1).limit(limit))
        for d in docs:
            d['id'] = str(d.pop('_id'))
        return docs
    except Exception as e:
        logger.error(f"mongo_candidates_for_ranking failed: {e}")
        return []


def mongo_set_embedding_cache(candidate_id: str, cache: dict) -> None:
    col = candidates_collection()
    if col is None or not cache:
        return
    try:
        from bson import ObjectId
        col.update_one({'_id': ObjectId(candidate_id)}, {'$set': {'embedding_cache': cache}})
    except Exception as e:
        logger.error(f"mongo_set_embedding_cache failed: {e}")


def rankings_collection():
    db = _get_db()
    return None if db is None else db['rankings']


def mongo_save_ranking(doc: dict) -> str | None:
    """Store one ranking run (JD, weights, per-candidate components)."""
    col = rankings_collection()
    if col is None:
        return None
    try:
        return str(col.insert_one({**doc, 'created_at': datetime.utcnow()}).inserted_id)
    except Exception as e:
        logger.error(f"mongo_save_ranking failed: {e}")
        return None


def mongo_get_ranking(ranking_id: str) -> dict | None:
    col = rankings_collection()
    if col is None:
        return None
    try:
        from bson import ObjectId
        doc = col.find_one({'_id': ObjectId(ranking_id)})
        if doc:
            doc['ranking_id'] = str(doc.pop('_id'))
        return doc
    except Exception as e:
        logger.error(f"mongo_get_ranking failed: {e}")
        return None
