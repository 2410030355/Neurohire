"""
Evaluation runner. Uses the production code paths (analysis_engine.analyze_text
and ranking.rank_candidates), so reported numbers are what the app computes.

Experiments per job:
  1. main         baselines vs NeuroHire variants (ablation), all metrics,
                  stratified-bootstrap 95% CIs, paired differences vs keyword
  2. weights      FS weight sensitivity (w_SS = 0 … 1)
  3. evidence     VS first-mention (paper) vs any-mention
  4. stuffing     keyword-stuffed copies of non-relevant résumés added to the
                  pool: do they climb into the top-k?
  5. fairness     counterfactual name swaps with redaction on vs off
  6. leakage      effect of leaving the "Ground Truth Label" line in the text
"""
from __future__ import annotations

import hashlib
from datetime import date
from typing import Callable, Dict, List, Optional

import numpy as np

from neurohire.analysis_engine import analyze_text
from neurohire.extraction import extract_skills
from neurohire.ranking import rank_candidates

from . import metrics as M
from .baselines import SIMILARITY_BACKENDS, baseline_scorers
from .data import Dataset, Job
from .perturb import COUNTERFACTUAL_NAMES, display_names, identity_variants, skill_stuff

# Revised method (default in the app): VS = JD-conditioned evidence,
# CS not applicable when no skills are recognised.
ABLATIONS = [
    ('NeuroHire: SS only', {'SS'}),
    ('NeuroHire: SS+CS', {'SS', 'CS'}),
    ('NeuroHire: SS+CS+VS', {'SS', 'CS', 'VS'}),
    ('NeuroHire: full (SS+CS+VS+LV)', {'SS', 'CS', 'VS', 'LV'}),
]
FULL = 'NeuroHire: full (SS+CS+VS+LV)'
# First formulation, for comparison: VS over all listed skills (first-mention
# window) and CS = 100 for profiles with no recognised skills.
FULL_ORIG = 'Original formulation: full'
ORIGINAL_ABLATIONS = [
    ('Original formulation: SS+CS+VS', {'SS', 'CS', 'VS'}),
    (FULL_ORIG, {'SS', 'CS', 'VS', 'LV'}),
]
REFERENCE = 'Keyword (skill overlap)'


class MemoSimilarity:
    """Similarity back-end with a memo, so repeated texts are scored once."""

    def __init__(self, backend: Callable):
        self.backend, self.memo, self.calls = backend, {}, 0

    def prefetch(self, texts, jd):
        """Score many texts in one backend call (fewer API requests)."""
        self(list(texts), jd)

    def __call__(self, texts, jd, caches=None):
        key = lambda t: hashlib.sha256(f'{jd}\x00{t}'.encode()).hexdigest()
        missing = [t for t in dict.fromkeys(texts) if key(t) not in self.memo]
        if missing:
            self.calls += 1
            out = self.backend(missing, jd)
            for t, s in zip(missing, out['scores']):
                self.memo[key(t)] = s
            self.method = out['method']
        return {'scores': [self.memo[key(t)] for t in texts], 'method': getattr(self, 'method', 'memo'),
                'new_embeddings': [None] * len(texts)}


_ANALYSES: Dict = {}


def analyze_cached(text: str, job: Job, ref: Optional[date], vs_mode='first', redact=True,
                   gemini_extraction=False) -> Dict:
    """
    analyze_text with SS skipped, cached per (text, options). Everything the
    evaluation uses (skills, CS, VS, LV, redacted text) is independent of the
    job description, so one analysis serves every job and label scheme.
    (Only jd_skills / missing_skills depend on the JD; the evaluation does not use them.)
    """
    key = (hashlib.sha256(text.encode()).hexdigest(), vs_mode, redact, gemini_extraction, str(ref))
    if key not in _ANALYSES:
        _ANALYSES[key] = analyze_text(text, job.title, job.jd, reference_date=ref, redact=redact,
                                      compute_similarity=False, use_gemini_extraction=gemini_extraction,
                                      vs_mode=vs_mode)
    return _ANALYSES[key]


def analyze_pool(texts: Dict[str, str], job: Job, ref: Optional[date], vs_mode='first',
                 redact=True, gemini_extraction=False) -> Dict[str, Dict]:
    return {rid: analyze_cached(text, job, ref, vs_mode, redact, gemini_extraction)
            for rid, text in texts.items()}


def to_candidates(analyses: Dict[str, Dict], original: bool = False) -> List[Dict]:
    """original=True reproduces the first formulation's CS (100 when no skills)."""
    out = []
    for rid, a in analyses.items():
        cs = a['consistency_score']
        if original and cs is None and not a['skills']:
            cs = 100.0
        out.append({'id': rid, 'name': rid, 'text': a['resume_text_redacted'], 'skills': a['skills'],
                    'experience_years': a['experience_years'], 'consistency_score': cs,
                    'skill_validation_score': a['skill_validation_score'],
                    'skill_validation_score_original': a['skill_validation_score_original'],
                    'lv_raw': a['lv_raw'], 'validated_skills_evidence': a['validated_skills_evidence']})
    return out


def nh_scores(cands: List[Dict], jd: str, sim, components, w_ss=None, vs_variant='jd') -> Dict[str, Dict]:
    w_as = None if w_ss is None else 1.0 - w_ss
    ranked = rank_candidates(cands, jd, sim, extract_skills, w_ss=w_ss, w_as=w_as, components=components,
                             vs_variant=vs_variant)
    return {r['candidate_id']: r for r in ranked['results']}


def _vector(d: Dict[str, float], ids: List[str]) -> List[float]:
    return [float(d[i]) for i in ids]


def evaluate_job(ds: Dataset, job: Job, similarity: str = 'tfidf', k: int = 5, n_boot: int = 2000,
                 seed: int = 42, gemini_extraction: bool = False, progress=print,
                 stuffing_sample: Optional[int] = None, fairness_sample: Optional[int] = None) -> Dict:
    ids = [r.id for r in ds.resumes]
    labels = [job.labels[i] for i in ids]
    texts = {r.id: r.text for r in ds.resumes}
    sim = MemoSimilarity(SIMILARITY_BACKENDS[similarity])
    ref = ds.reference_date

    progress(f'[{job.id}] analysing {len(ids)} résumés')
    pool = analyze_pool(texts, job, ref, 'first', True, gemini_extraction)
    pool_any = analyze_pool(texts, job, ref, 'any', True, gemini_extraction)
    cands, cands_any = to_candidates(pool), to_candidates(pool_any, original=True)
    cands_orig = to_candidates(pool, original=True)
    redacted = [pool[i]['resume_text_redacted'] for i in ids]

    # ── 1. main comparison ────────────────────────────────────────────────
    progress(f'[{job.id}] baselines and ablations')
    method_scores: Dict[str, List[float]] = {}
    for name, fn in baseline_scorers(similarity, sim).items():
        method_scores[name] = [float(x) for x in fn(redacted, job.jd)]
    nh_detail = {}
    for name, comps in ABLATIONS:
        res = nh_scores(cands, job.jd, sim, comps)
        nh_detail[name] = res
        method_scores[name] = _vector({i: res[i]['final_score'] for i in ids}, ids)
    for name, comps in ORIGINAL_ABLATIONS:
        res = nh_scores(cands_orig, job.jd, sim, comps, vs_variant='original')
        nh_detail[name] = res
        method_scores[name] = _vector({i: res[i]['final_score'] for i in ids}, ids)

    main = {m: M.evaluate_scores(s, labels, k=k, seed=seed) for m, s in method_scores.items()}
    progress(f'[{job.id}] bootstrap ({n_boot} replicates)')
    boot = M.stratified_bootstrap(method_scores, labels, k=k, n_boot=n_boot, seed=seed,
                                  metrics=('AP', f'NDCG@{k}', f'P@{k}', 'AUC'), reference=REFERENCE,
                                  return_draws=True)
    draws = boot.pop('_draws')

    # ── 2. weight sensitivity ─────────────────────────────────────────────
    weights = []
    for w in np.round(np.arange(0, 1.0001, 0.1), 2):
        row = {'w_ss': float(w), 'w_as': round(1 - float(w), 2)}
        for tag, variant, cs_ in (('', 'jd', cands), ('O_', 'original', cands_orig)):
            res = nh_scores(cs_, job.jd, sim, {'SS', 'CS', 'VS', 'LV'}, w_ss=float(w), vs_variant=variant)
            sc = _vector({i: res[i]['final_score'] for i in ids}, ids)
            e = M.evaluate_scores(sc, labels, k=k, seed=seed)
            row.update({f'{tag}{x}': e[x] for x in ('AP', f'NDCG@{k}', f'P@{k}', 'AUC')})
        weights.append(row)

    # ── 3. evidence: which VS definition ──────────────────────────────────
    res_any = nh_scores(cands_any, job.jd, sim, {'SS', 'CS', 'VS', 'LV'}, vs_variant='original')
    any_scores = _vector({i: res_any[i]['final_score'] for i in ids}, ids)

    def _mean(vals):
        vals = [v for v in vals if v is not None]
        return float(np.mean(vals)) if vals else None
    evidence = {
        'JD-conditioned evidence (revised)': {**main[FULL],
            'mean_VS': _mean([nh_detail[FULL][i]['skill_validation_score'] for i in ids])},
        'original: all skills, first mention': {**main[FULL_ORIG],
            'mean_VS': _mean([pool[i]['skill_validation_score_original'] for i in ids])},
        'original: all skills, any mention': {**M.evaluate_scores(any_scores, labels, k=k, seed=seed),
            'mean_VS': _mean([pool_any[i]['skill_validation_score_original'] for i in ids])},
    }
    method_scores_any = {FULL: method_scores[FULL], FULL_ORIG: method_scores[FULL_ORIG],
                         'Original formulation: full, any-mention VS': any_scores}

    # ── 4. keyword stuffing ───────────────────────────────────────────────
    progress(f'[{job.id}] keyword-stuffing robustness')
    stuffing = stuffing_experiment(ids, labels, texts, pool, job, ref, sim, similarity, k, seed,
                                   gemini_extraction, n_boot, stuffing_sample)

    # ── 5. counterfactual fairness ────────────────────────────────────────
    progress(f'[{job.id}] counterfactual fairness (redaction on / off)')
    subjects = _sample(ids, fairness_sample, seed)
    fairness = {
        'redaction on': fairness_experiment(ids, texts, pool, job, ref, sim, True, gemini_extraction, subjects),
        'redaction off': fairness_experiment(ids, texts, None, job, ref, sim, False, gemini_extraction, subjects),
    }

    # ── 6. label leakage ──────────────────────────────────────────────────
    leakage = leakage_check(ds, job, sim)

    per_candidate = []
    for i, rid in enumerate(ids):
        a, r = pool[rid], nh_detail[FULL][rid]
        per_candidate.append({
            'id': rid, 'label': labels[i], 'rank_full': r['rank'],
            'FS': r['final_score'], 'SS': r['semantic_score'], 'CS': r['consistency_score'],
            'VS': r['skill_validation_score'], 'LV': r['lv_score'], 'LV_raw': a['lv_raw'],
            'AS': r['analytical_score'], 'fit': r['final_fit'],
            'VS_original': a['skill_validation_score_original'],
            'FS_original': nh_detail[FULL_ORIG][rid]['final_score'],
            'rank_original': nh_detail[FULL_ORIG][rid]['rank'],
            'VS_original_any': pool_any[rid]['skill_validation_score_original'],
            'experience_dated': a['experience_years_dated'], 'experience_claimed': a['experience_years_claimed'],
            'n_skills': len(a['skills']), 'skills': ' '.join(a['skills']),
            'cs_flags': '; '.join(f['rule'] for f in a['consistency_flags']),
            **{f'score[{m}]': method_scores[m][i] for m in method_scores},
        })

    return {
        'job': {'id': job.id, 'title': job.title, 'jd': job.jd, 'jd_note': job.jd_note,
                'source': job.source, 'scheme': job.scheme, 'relevant_categories': job.relevant_categories,
                'n': len(ids), 'n_relevant': sum(1 for l in labels if l > 0)},
        '_draws': draws,
        'main': main, 'bootstrap': boot, 'weights': weights,
        'evidence': evidence,
        'evidence_bootstrap': M.stratified_bootstrap(method_scores_any, labels, k=k, n_boot=n_boot, seed=seed,
                                                     metrics=('AP', f'NDCG@{k}', 'AUC'), reference=FULL),
        'stuffing': stuffing, 'fairness': fairness, 'leakage': leakage,
        'per_candidate': per_candidate, 'similarity_backend_calls': sim.calls,
        'cs_constant': len({pool[i]['consistency_score'] for i in ids}) == 1,
    }


def _sample(items: List[str], n: Optional[int], seed: int) -> List[str]:
    """Seeded sample (all items when n is None or larger than the list)."""
    if not n or n >= len(items):
        return list(items)
    rng = np.random.default_rng(seed)
    return sorted(rng.choice(items, n, replace=False).tolist())


def stuffing_experiment(ids, labels, texts, pool, job, ref, sim, similarity, k, seed, gemini_extraction,
                        n_boot=2000, sample=None):
    jd_skills = extract_skills(job.jd)
    negatives = _sample([i for i, l in zip(ids, labels) if l <= 0], sample, seed)
    stuffed_texts = {f'{i}__stuffed': skill_stuff(texts[i], display_names(jd_skills)) for i in negatives}
    stuffed_pool = analyze_pool(stuffed_texts, job, ref, 'first', True, gemini_extraction)
    sim.prefetch([a['resume_text_redacted'] for a in stuffed_pool.values()], job.jd)
    aug_ids = ids + list(stuffed_texts)
    aug_labels = labels + [0] * len(stuffed_texts)
    aug_pool = {**pool, **stuffed_pool}
    aug_texts = [aug_pool[i]['resume_text_redacted'] for i in aug_ids]
    cands = to_candidates({i: aug_pool[i] for i in aug_ids})
    cands_orig = to_candidates({i: aug_pool[i] for i in aug_ids}, original=True)

    scores = {name: [float(x) for x in fn(aug_texts, job.jd)]
              for name, fn in baseline_scorers(similarity, sim).items()}
    for name, comps in ABLATIONS:
        res = nh_scores(cands, job.jd, sim, comps)
        scores[name] = [res[i]['final_score'] for i in aug_ids]
    for name, comps in ORIGINAL_ABLATIONS:
        res = nh_scores(cands_orig, job.jd, sim, comps, vs_variant='original')
        scores[name] = [res[i]['final_score'] for i in aug_ids]

    out = {'stuffed_skills': jd_skills, 'n_stuffed': len(stuffed_texts), 'n_negatives_total':
           sum(1 for l in labels if l <= 0), 'methods': {}}
    rng = np.random.default_rng(seed)
    for name, sc in scores.items():
        e = M.evaluate_scores(sc, aug_labels, k=k, seed=seed)
        order = sorted(range(len(sc)), key=lambda j: (-sc[j], rng.random()))
        rank = {aug_ids[j]: r + 1 for r, j in enumerate(order)}
        stuffed = [i for i in aug_ids if i.endswith('__stuffed')]
        gains = [rank[s.replace('__stuffed', '')] - rank[s] for s in stuffed]
        out['methods'][name] = {
            'AP': e['AP'], f'NDCG@{k}': e[f'NDCG@{k}'], f'P@{k}': e[f'P@{k}'], 'AUC': e['AUC'],
            f'stuffed_in_top{k}': sum(1 for s in stuffed if rank[s] <= k),
            'mean_rank_gain': float(np.mean(gains)),
            'mean_score_gain_pct': float(np.mean([
                (sc[aug_ids.index(s)] - sc[aug_ids.index(s.replace('__stuffed', ''))])
                / (abs(sc[aug_ids.index(s.replace('__stuffed', ''))]) or 1) * 100 for s in stuffed])),
        }
    out['bootstrap_vs_ss_only'] = M.stratified_bootstrap(scores, aug_labels, k=k, n_boot=n_boot, seed=seed,
                                                         metrics=('AP', f'NDCG@{k}', 'AUC'),
                                                         reference='NeuroHire: SS only', return_draws=True)
    out['_draws'] = out['bootstrap_vs_ss_only'].pop('_draws')
    out['stuffed_VS'] = {s: stuffed_pool[s]['skill_validation_score'] for s in stuffed_pool}
    out['original_VS'] = {i: pool[i]['skill_validation_score'] for i in negatives}
    return out


def fairness_experiment(ids, texts, pool, job, ref, sim, redact, gemini_extraction, subjects=None):
    base_pool = pool if pool is not None else analyze_pool(texts, job, ref, 'first', redact, gemini_extraction)
    base = nh_scores(to_candidates(base_pool), job.jd, sim, {'SS', 'CS', 'VS', 'LV'})
    deltas, rank_moves, by_group = [], [], {}
    per_candidate = {}
    # Analyse every variant first and score their texts in one batch
    variant_analyses = {
        rid: {vname: analyze_cached(vtext, job, ref, 'first', redact, gemini_extraction)
              for vname, vtext in identity_variants(texts[rid]).items()}
        for rid in (subjects or ids)
    }
    sim.prefetch([va['resume_text_redacted'] for v in variant_analyses.values() for va in v.values()], job.jd)
    for rid in (subjects or ids):
        cand_deltas = []
        for vname, va in variant_analyses[rid].items():
            swapped = dict(base_pool)
            swapped[rid] = va
            res = nh_scores(to_candidates(swapped), job.jd, sim, {'SS', 'CS', 'VS', 'LV'})
            d = res[rid]['final_score'] - base[rid]['final_score']
            deltas.append(abs(d))
            cand_deltas.append(d)
            rank_moves.append(abs(res[rid]['rank'] - base[rid]['rank']))
            group = vname.split(':')[0]
            by_group.setdefault(group, []).append(res[rid]['final_score'])
        per_candidate[rid] = {'max_abs_dFS': float(max(abs(x) for x in cand_deltas))}
    female = [s for g, v in by_group.items() if g.startswith('female') for s in v]
    male = [s for g, v in by_group.items() if g.startswith('male') for s in v]
    return {
        'variants_per_candidate': len(COUNTERFACTUAL_NAMES),
        'candidates_tested': len(subjects or ids),
        'mean_abs_dFS': float(np.mean(deltas)), 'max_abs_dFS': float(np.max(deltas)),
        'max_abs_rank_change': int(np.max(rank_moves)),
        'share_rank_changed': float(np.mean([m > 0 for m in rank_moves])),
        'gender_gap_mean_FS': float(np.mean(female) - np.mean(male)),
        'group_mean_FS': {g: float(np.mean(v)) for g, v in by_group.items()},
        'per_candidate': per_candidate,
    }


def leakage_check(ds: Dataset, job: Job, sim) -> Dict:
    """TF-IDF/embedding SS with vs without the label line (the app strips it)."""
    from .data import read_text
    raw = {r.id: read_text(r.path) for r in ds.resumes}
    with_label = [raw[r.id] for r in ds.resumes]
    without = [r.text for r in ds.resumes]
    s_with = sim(with_label, job.jd)['scores']
    s_without = sim(without, job.jd)['scores']
    diffs = [a - b for a, b in zip(s_with, s_without) if a is not None and b is not None]
    return {'mean_SS_change_if_label_left_in': float(np.mean(diffs)) if diffs else 0.0,
            'max_SS_change_if_label_left_in': float(np.max(np.abs(diffs))) if diffs else 0.0,
            'note': 'analysis_engine strips this line before scoring; shown only to document the risk.'}
