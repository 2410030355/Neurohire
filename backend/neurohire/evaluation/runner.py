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

ABLATIONS = [
    ('NeuroHire: SS only', {'SS'}),
    ('NeuroHire: SS+CS', {'SS', 'CS'}),
    ('NeuroHire: SS+CS+VS', {'SS', 'CS', 'VS'}),
    ('NeuroHire: full (SS+CS+VS+LV)', {'SS', 'CS', 'VS', 'LV'}),
]
FULL = 'NeuroHire: full (SS+CS+VS+LV)'
FULL_JD = 'NeuroHire-E: full, JD-conditioned evidence'
JD_ABLATIONS = [
    ('NeuroHire-E: SS+VS_JD', {'SS', 'VS'}),
    (FULL_JD, {'SS', 'CS', 'VS', 'LV'}),
]
REFERENCE = 'Keyword (skill overlap)'


class MemoSimilarity:
    """Similarity back-end with a memo, so repeated texts are scored once."""

    def __init__(self, backend: Callable):
        self.backend, self.memo, self.calls = backend, {}, 0

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


def analyze_pool(texts: Dict[str, str], job: Job, ref: Optional[date], vs_mode='first',
                 redact=True, gemini_extraction=False) -> Dict[str, Dict]:
    out = {}
    for rid, text in texts.items():
        a = analyze_text(text, job.title, job.jd, reference_date=ref, redact=redact,
                         compute_similarity=False, use_gemini_extraction=gemini_extraction,
                         vs_mode=vs_mode)
        out[rid] = a
    return out


def to_candidates(analyses: Dict[str, Dict]) -> List[Dict]:
    return [{'id': rid, 'name': rid, 'text': a['resume_text_redacted'], 'skills': a['skills'],
             'experience_years': a['experience_years'], 'consistency_score': a['consistency_score'],
             'skill_validation_score': a['skill_validation_score'], 'lv_raw': a['lv_raw'],
             'validated_skills_evidence': a['validated_skills_evidence']}
            for rid, a in analyses.items()]


def nh_scores(cands: List[Dict], jd: str, sim, components, w_ss=None, vs_variant='paper') -> Dict[str, Dict]:
    w_as = None if w_ss is None else 1.0 - w_ss
    ranked = rank_candidates(cands, jd, sim, extract_skills, w_ss=w_ss, w_as=w_as, components=components,
                             vs_variant=vs_variant)
    return {r['candidate_id']: r for r in ranked['results']}


def _vector(d: Dict[str, float], ids: List[str]) -> List[float]:
    return [float(d[i]) for i in ids]


def evaluate_job(ds: Dataset, job: Job, similarity: str = 'tfidf', k: int = 5, n_boot: int = 2000,
                 seed: int = 42, gemini_extraction: bool = False, progress=print) -> Dict:
    ids = [r.id for r in ds.resumes]
    labels = [job.labels[i] for i in ids]
    texts = {r.id: r.text for r in ds.resumes}
    sim = MemoSimilarity(SIMILARITY_BACKENDS[similarity])
    ref = ds.reference_date

    progress(f'[{job.id}] analysing {len(ids)} résumés')
    pool = analyze_pool(texts, job, ref, 'first', True, gemini_extraction)
    pool_any = analyze_pool(texts, job, ref, 'any', True, gemini_extraction)
    cands, cands_any = to_candidates(pool), to_candidates(pool_any)
    redacted = [pool[i]['resume_text_redacted'] for i in ids]

    # ── 1. main comparison ────────────────────────────────────────────────
    progress(f'[{job.id}] baselines and ablations')
    method_scores: Dict[str, List[float]] = {}
    for name, fn in baseline_scorers(similarity).items():
        method_scores[name] = [float(x) for x in fn(redacted, job.jd)]
    nh_detail = {}
    for name, comps in ABLATIONS:
        res = nh_scores(cands, job.jd, sim, comps)
        nh_detail[name] = res
        method_scores[name] = _vector({i: res[i]['final_score'] for i in ids}, ids)
    for name, comps in JD_ABLATIONS:
        res = nh_scores(cands, job.jd, sim, comps, vs_variant='jd')
        nh_detail[name] = res
        method_scores[name] = _vector({i: res[i]['final_score'] for i in ids}, ids)

    main = {m: M.evaluate_scores(s, labels, k=k, seed=seed) for m, s in method_scores.items()}
    progress(f'[{job.id}] bootstrap ({n_boot} replicates)')
    boot = M.stratified_bootstrap(method_scores, labels, k=k, n_boot=n_boot, seed=seed,
                                  metrics=('AP', f'NDCG@{k}', f'P@{k}', 'AUC'), reference=REFERENCE)

    # ── 2. weight sensitivity ─────────────────────────────────────────────
    weights = []
    for w in np.round(np.arange(0, 1.0001, 0.1), 2):
        row = {'w_ss': float(w), 'w_as': round(1 - float(w), 2)}
        for tag, variant in (('', 'paper'), ('E_', 'jd')):
            res = nh_scores(cands, job.jd, sim, {'SS', 'CS', 'VS', 'LV'}, w_ss=float(w), vs_variant=variant)
            sc = _vector({i: res[i]['final_score'] for i in ids}, ids)
            e = M.evaluate_scores(sc, labels, k=k, seed=seed)
            row.update({f'{tag}{x}': e[x] for x in ('AP', f'NDCG@{k}', f'P@{k}', 'AUC')})
        weights.append(row)

    # ── 3. evidence: VS first vs any mention ──────────────────────────────
    res_any = nh_scores(cands_any, job.jd, sim, {'SS', 'CS', 'VS', 'LV'})
    any_scores = _vector({i: res_any[i]['final_score'] for i in ids}, ids)
    evidence = {
        'first-mention (paper)': {**main[FULL],
                                  'mean_VS': float(np.mean([pool[i]['skill_validation_score'] or 0 for i in ids]))},
        'any-mention': {**M.evaluate_scores(any_scores, labels, k=k, seed=seed),
                        'mean_VS': float(np.mean([pool_any[i]['skill_validation_score'] or 0 for i in ids]))},
    }
    method_scores_any = {FULL: method_scores[FULL], 'NeuroHire: full, VS any-mention': any_scores}

    # ── 4. keyword stuffing ───────────────────────────────────────────────
    progress(f'[{job.id}] keyword-stuffing robustness')
    stuffing = stuffing_experiment(ids, labels, texts, pool, job, ref, sim, similarity, k, seed,
                                   gemini_extraction, n_boot)

    # ── 5. counterfactual fairness ────────────────────────────────────────
    progress(f'[{job.id}] counterfactual fairness (redaction on / off)')
    fairness = {
        'redaction on': fairness_experiment(ids, texts, pool, job, ref, sim, True, gemini_extraction),
        'redaction off': fairness_experiment(ids, texts, None, job, ref, sim, False, gemini_extraction),
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
            'VS_JD': nh_detail[FULL_JD][rid]['skill_validation_score'],
            'FS_E': nh_detail[FULL_JD][rid]['final_score'], 'rank_E': nh_detail[FULL_JD][rid]['rank'],
            'VS_any': pool_any[rid]['skill_validation_score'],
            'experience_dated': a['experience_years_dated'], 'experience_claimed': a['experience_years_claimed'],
            'n_skills': len(a['skills']), 'skills': ' '.join(a['skills']),
            'cs_flags': '; '.join(f['rule'] for f in a['consistency_flags']),
            **{f'score[{m}]': method_scores[m][i] for m in method_scores},
        })

    return {
        'job': {'id': job.id, 'title': job.title, 'jd': job.jd, 'jd_note': job.jd_note,
                'n': len(ids), 'n_relevant': sum(1 for l in labels if l > 0)},
        'main': main, 'bootstrap': boot, 'weights': weights,
        'evidence': evidence,
        'evidence_bootstrap': M.stratified_bootstrap(method_scores_any, labels, k=k, n_boot=n_boot, seed=seed,
                                                     metrics=('AP', f'NDCG@{k}', 'AUC'), reference=FULL),
        'stuffing': stuffing, 'fairness': fairness, 'leakage': leakage,
        'per_candidate': per_candidate, 'similarity_backend_calls': sim.calls,
        'cs_constant': len({pool[i]['consistency_score'] for i in ids}) == 1,
    }


def stuffing_experiment(ids, labels, texts, pool, job, ref, sim, similarity, k, seed, gemini_extraction,
                        n_boot=2000):
    jd_skills = extract_skills(job.jd)
    negatives = [i for i, l in zip(ids, labels) if l <= 0]
    stuffed_texts = {f'{i}__stuffed': skill_stuff(texts[i], display_names(jd_skills)) for i in negatives}
    stuffed_pool = analyze_pool(stuffed_texts, job, ref, 'first', True, gemini_extraction)
    aug_ids = ids + list(stuffed_texts)
    aug_labels = labels + [0] * len(stuffed_texts)
    aug_pool = {**pool, **stuffed_pool}
    aug_texts = [aug_pool[i]['resume_text_redacted'] for i in aug_ids]
    cands = to_candidates({i: aug_pool[i] for i in aug_ids})

    scores = {name: [float(x) for x in fn(aug_texts, job.jd)] for name, fn in baseline_scorers(similarity).items()}
    for name, comps in ABLATIONS:
        res = nh_scores(cands, job.jd, sim, comps)
        scores[name] = [res[i]['final_score'] for i in aug_ids]
    for name, comps in JD_ABLATIONS:
        res = nh_scores(cands, job.jd, sim, comps, vs_variant='jd')
        scores[name] = [res[i]['final_score'] for i in aug_ids]

    out = {'stuffed_skills': jd_skills, 'n_stuffed': len(stuffed_texts), 'methods': {}}
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
                                                         reference='NeuroHire: SS only')
    out['stuffed_VS'] = {s: stuffed_pool[s]['skill_validation_score'] for s in stuffed_pool}
    out['original_VS'] = {i: pool[i]['skill_validation_score'] for i in negatives}
    return out


def fairness_experiment(ids, texts, pool, job, ref, sim, redact, gemini_extraction):
    base_pool = pool if pool is not None else analyze_pool(texts, job, ref, 'first', redact, gemini_extraction)
    base = nh_scores(to_candidates(base_pool), job.jd, sim, {'SS', 'CS', 'VS', 'LV'})
    deltas, rank_moves, by_group = [], [], {}
    per_candidate = {}
    for rid in ids:
        variants = identity_variants(texts[rid])
        cand_deltas = []
        for vname, vtext in variants.items():
            va = analyze_text(vtext, job.title, job.jd, reference_date=ref, redact=redact,
                              compute_similarity=False, use_gemini_extraction=gemini_extraction)
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
