"""
ranking.py — rank stored candidates against one job description (paper §IV.E.3).

    for each candidate:  SS against this JD (recomputed), CS and VS as stored
                         (they do not depend on the JD), LV_raw as stored
    LV normalisation:    min–max over the candidates being ranked (the paper's
                         "normalisation set")
    AS, FS:              scoring.score_candidate
    order:               FS desc, then SS desc, then name (deterministic ties)

Pure and database-free: the API view and the evaluation scripts call the same
function, so the numbers in the paper are the numbers the app produces.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from . import scoring


def rank_candidates(candidates: List[Dict], job_description: str,
                    similarity_batch_fn: Callable[[List[str], str, List[Optional[dict]]], Dict],
                    extract_skills_fn: Optional[Callable[[str], List[str]]] = None,
                    w_ss: Optional[float] = None, w_as: Optional[float] = None,
                    components: Optional[set] = None, vs_variant: str = 'paper') -> Dict:
    """
    candidates: dicts with keys
        id, name, text (redacted résumé text), skills,
        consistency_score, skill_validation_score, lv_raw,
        embedding_cache (optional; passed through to similarity_batch_fn)
    components: which of {'SS','CS','VS','LV'} to use (ablation). Default all.
    vs_variant: 'paper' = stored VS (§IV.D.2); 'jd' = JD-conditioned evidence
                (scoring.compute_jd_evidence; needs validated_skills_evidence).
    Returns {'results': [...ranked...], 'method': str, 'lv_bounds': {...},
             'weights': {...}, 'new_embeddings': [...aligned with input...]}
    """
    components = set(components or {'SS', 'CS', 'VS', 'LV'})
    texts = [c.get('text') or '' for c in candidates]
    caches = [c.get('embedding_cache') for c in candidates]
    sim = similarity_batch_fn(texts, job_description, caches)

    lv_raw = [c.get('lv_raw') for c in candidates]
    lv_norm = scoring.normalize_lv_batch(lv_raw)
    present = [v for v in lv_raw if v is not None]

    jd_skills = set(extract_skills_fn(job_description)) if extract_skills_fn else set()
    if vs_variant == 'jd' and not extract_skills_fn:
        raise ValueError("vs_variant='jd' needs extract_skills_fn")

    results = []
    for i, c in enumerate(candidates):
        ss = sim['scores'][i] if 'SS' in components else None
        cs = c.get('consistency_score') if 'CS' in components else None
        if 'VS' not in components:
            vs = None
        elif vs_variant == 'jd':
            vs = scoring.compute_jd_evidence(c.get('validated_skills_evidence') or [], jd_skills)
        else:
            vs = c.get('skill_validation_score')
        raw = lv_raw[i] if 'LV' in components else None
        norm = lv_norm[i] if 'LV' in components else None
        s = scoring.score_candidate(ss, cs, vs, raw, w_ss=w_ss, w_as=w_as, lv_norm=norm)
        if norm is None:
            s['lv_score'] = None
        skills = set(c.get('skills') or [])
        results.append({
            'candidate_id': c.get('id'),
            'name': c.get('name') or 'Candidate',
            **s,
            'matched_skills': sorted(jd_skills & skills),
            'missing_skills': sorted(jd_skills - skills),
            'experience_years': c.get('experience_years'),
            'learning_velocity': scoring.lv_label(s['lv_score']),
        })

    results.sort(key=lambda r: (-r['final_score'],
                                -(r['semantic_score'] if r['semantic_score'] is not None else -1),
                                str(r['name']).lower()))
    for rank, r in enumerate(results, start=1):
        r['rank'] = rank

    return {
        'results': results,
        'method': sim['method'],
        'lv_bounds': {'min': min(present) if present else None,
                      'max': max(present) if present else None,
                      'n_with_lv': len(present)},
        'weights': {'SS': scoring.W_SS if w_ss is None else w_ss,
                    'AS': scoring.W_AS if w_as is None else w_as},
        'components': sorted(components),
        'vs_variant': vs_variant,
        'jd_skills': sorted(jd_skills),
        'new_embeddings': sim.get('new_embeddings', [None] * len(candidates)),
    }
