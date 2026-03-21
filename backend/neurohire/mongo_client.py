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

        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
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

def mongo_insert_candidate(data: dict) -> str | None:
    """
    Insert a candidate profile document.
    Adds created_at timestamp automatically.
    Returns the inserted _id as string, or None on failure.
    """
    col = candidates_collection()
    if col is None:
        return None
    try:
        doc = {**data, 'created_at': datetime.utcnow()}
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
        doc = col.find_one({'_id': ObjectId(mongo_id)})
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
        docs = list(col.find().sort('created_at', -1).limit(limit))
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