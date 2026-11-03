"""
feedback.py — recruiter-feedback weight adjustment (paper §IV.H).

Update rule, specified fully for reproducibility:

    d  = +1 (hire / select), −1 (reject); waitlist / hold → no update
    s  = d · sign(SS − AS)       the feedback signal is attributed to the
                                 component that dominated this candidate's score
    w_SS ← clip(w_SS + η·s, 0.1, 0.9)
    w_AS ← 1 − w_SS              (normalisation: weights sum to one)
    η  = 0.05

Intuition: hiring a candidate whose semantic score exceeded their analytical
score moves weight toward SS; rejecting such a candidate moves it toward AS.
SS = AS gives s = 0 (no update). A changed decision applies s_new − s_old,
so flipping hire → reject reverses the earlier update and applies the new one.

Weights live in MongoDB (collection 'feedback_weights', document 'current')
with an append-only history ('feedback_history'), so they survive restarts.
They are only USED for scoring when ADAPTIVE_WEIGHTS=1; by default FS uses the
configured 0.6 / 0.4 and the learned weights are recorded and displayed only
(the paper does not claim that adaptation improves ranking).
"""
from __future__ import annotations

import logging
import os
import threading
from datetime import datetime
from typing import Dict, Optional

from . import scoring

logger = logging.getLogger(__name__)

ETA = float(os.environ.get('FEEDBACK_LEARNING_RATE', '0.05'))
W_MIN, W_MAX = 0.1, 0.9
DECISION_SIGN = {'hire': 1, 'accept': 1, 'select': 1, 'reject': -1}

_lock = threading.Lock()
_memory_state: Dict = {}          # used when MongoDB is unavailable


def adaptive_enabled() -> bool:
    return os.environ.get('ADAPTIVE_WEIGHTS', '0').strip() == '1'


def default_weights() -> Dict:
    total = scoring.W_SS + scoring.W_AS
    return {'w_ss': round(scoring.W_SS / total, 6), 'w_as': round(scoring.W_AS / total, 6), 'version': 0}


# ── Pure rule ─────────────────────────────────────────────────────────────

def decision_sign(decision: Optional[str]) -> int:
    return DECISION_SIGN.get((decision or '').strip().lower(), 0)


def feedback_signal(decision: Optional[str], ss: Optional[float], as_score: Optional[float]) -> int:
    """s = d · sign(SS − AS); 0 when the decision is neutral or a score is missing."""
    d = decision_sign(decision)
    if d == 0 or ss is None or as_score is None:
        return 0
    diff = float(ss) - float(as_score)
    return 0 if diff == 0 else d * (1 if diff > 0 else -1)


def apply_signal(w_ss: float, s: float, eta: float = ETA) -> Dict:
    """w_SS ← clip(w_SS + η·s, 0.1, 0.9); w_AS ← 1 − w_SS."""
    new_ss = min(W_MAX, max(W_MIN, w_ss + eta * s))
    return {'w_ss': round(new_ss, 6), 'w_as': round(1.0 - new_ss, 6)}


# ── Persistence ───────────────────────────────────────────────────────────

def _collections():
    try:
        from .mongo_client import _get_db
        db = _get_db()
    except Exception:
        db = None
    if db is None:
        return None, None
    return db['feedback_weights'], db['feedback_history']


def get_learned_weights() -> Dict:
    """Current learned weights (defaults until the first update)."""
    state, _ = _collections()
    if state is not None:
        try:
            doc = state.find_one({'_id': 'current'})
            if doc:
                return {'w_ss': doc['w_ss'], 'w_as': doc['w_as'], 'version': doc.get('version', 0),
                        'updated_at': doc.get('updated_at')}
        except Exception as e:
            logger.error(f"Reading feedback weights failed: {e}")
    return dict(_memory_state) if _memory_state else default_weights()


def get_scoring_weights() -> Dict:
    """Weights FS should use: learned ones only when ADAPTIVE_WEIGHTS=1."""
    if adaptive_enabled():
        w = get_learned_weights()
        return {'w_ss': w['w_ss'], 'w_as': w['w_as'], 'source': 'learned'}
    d = default_weights()
    return {'w_ss': d['w_ss'], 'w_as': d['w_as'], 'source': 'configured'}


def record_feedback(decision: str, ss: Optional[float], as_score: Optional[float],
                    previous_decision: Optional[str] = None, context: Optional[Dict] = None) -> Dict:
    """
    Apply one recruiter decision. Returns
    {'updated': bool, 's': ..., 'before': {...}, 'after': {...}, 'reason': str}.
    """
    s_new = feedback_signal(decision, ss, as_score)
    s_old = feedback_signal(previous_decision, ss, as_score) if previous_decision else 0
    s = s_new - s_old
    with _lock:
        before = get_learned_weights()
        if s == 0:
            reason = ('neutral decision' if decision_sign(decision) == 0 and not previous_decision
                      else 'SS or AS unavailable' if ss is None or as_score is None
                      else 'SS equals AS' if s_new == 0 and s_old == 0
                      else 'no net change')
            return {'updated': False, 's': 0, 'before': before, 'after': before, 'reason': reason}

        after = apply_signal(before['w_ss'], s)
        after['version'] = int(before.get('version', 0)) + 1
        after['updated_at'] = datetime.utcnow()

        state, history = _collections()
        if state is not None:
            try:
                state.update_one({'_id': 'current'}, {'$set': after}, upsert=True)
                history.insert_one({
                    'version': after['version'], 'decision': decision, 'previous_decision': previous_decision,
                    's': s, 'semantic_score': ss, 'analytical_score': as_score, 'eta': ETA,
                    'before': {'w_ss': before['w_ss'], 'w_as': before['w_as']},
                    'after': {'w_ss': after['w_ss'], 'w_as': after['w_as']},
                    'context': context or {}, 'created_at': after['updated_at'],
                })
            except Exception as e:
                logger.error(f"Saving feedback weights failed: {e}")
        else:
            _memory_state.clear()
            _memory_state.update(after)

        logger.info(f"Feedback weights v{after['version']}: w_SS {before['w_ss']} → {after['w_ss']} (s={s})")
        return {'updated': True, 's': s, 'before': before, 'after': after, 'reason': 'applied'}


def feedback_history(limit: int = 50) -> list:
    _, history = _collections()
    if history is None:
        return []
    try:
        rows = list(history.find({}, {'_id': 0}).sort('version', -1).limit(limit))
        return rows
    except Exception as e:
        logger.error(f"Reading feedback history failed: {e}")
        return []


def reset_weights() -> Dict:
    """Back to the configured weights (history is kept)."""
    with _lock:
        d = default_weights()
        before = get_learned_weights()
        d['version'] = int(before.get('version', 0)) + 1
        d['updated_at'] = datetime.utcnow()
        state, history = _collections()
        if state is not None:
            state.update_one({'_id': 'current'}, {'$set': d}, upsert=True)
            history.insert_one({'version': d['version'], 'decision': 'reset', 's': 0,
                                'before': {'w_ss': before['w_ss'], 'w_as': before['w_as']},
                                'after': {'w_ss': d['w_ss'], 'w_as': d['w_as']},
                                'created_at': d['updated_at']})
        else:
            _memory_state.clear()
            _memory_state.update(d)
        return d
