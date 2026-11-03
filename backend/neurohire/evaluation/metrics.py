"""
Ranking metrics, tie handling, bootstrap confidence intervals, paired tests and
inter-annotator agreement. Pure Python + numpy, no Django.

Conventions
  labels   relevance per candidate (0 = not relevant, 1 = relevant; graded ok)
  scores   higher = ranked earlier
  Ties are NOT broken by input order (that silently favours whichever candidate
  happens to come first). Metrics are averaged over random tie-breaks with a
  fixed seed, i.e. the expected value under arbitrary tie-breaking.
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np


# ── Metrics on a ranked list of relevance labels ────────────────────────────

def precision_at_k(rels: Sequence[float], k: int) -> float:
    return sum(1 for r in rels[:k] if r > 0) / k


def recall_at_k(rels: Sequence[float], k: int) -> float:
    total = sum(1 for r in rels if r > 0)
    return sum(1 for r in rels[:k] if r > 0) / total if total else 0.0


def dcg_at_k(rels: Sequence[float], k: int) -> float:
    return sum((2 ** r - 1) / math.log2(i + 2) for i, r in enumerate(rels[:k]))


def ndcg_at_k(rels: Sequence[float], k: int) -> float:
    ideal = dcg_at_k(sorted(rels, reverse=True), k)
    return dcg_at_k(rels, k) / ideal if ideal > 0 else 0.0


def average_precision(rels: Sequence[float]) -> float:
    hits, total = 0, 0.0
    for i, r in enumerate(rels, start=1):
        if r > 0:
            hits += 1
            total += hits / i
    n_rel = sum(1 for r in rels if r > 0)
    return total / n_rel if n_rel else 0.0


def r_precision(rels: Sequence[float]) -> float:
    n_rel = sum(1 for r in rels if r > 0)
    return precision_at_k(rels, n_rel) if n_rel else 0.0


def reciprocal_rank(rels: Sequence[float]) -> float:
    for i, r in enumerate(rels, start=1):
        if r > 0:
            return 1.0 / i
    return 0.0


def auc(scores: Sequence[float], labels: Sequence[float]) -> float:
    """P(random relevant scored above random non-relevant); ties count 0.5."""
    pos = [s for s, l in zip(scores, labels) if l > 0]
    neg = [s for s, l in zip(scores, labels) if l <= 0]
    if not pos or not neg:
        return float('nan')
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def metric_suite(k: int = 5) -> Dict[str, Callable[[Sequence[float]], float]]:
    return {
        f'P@{k}': lambda r: precision_at_k(r, k),
        f'R@{k}': lambda r: recall_at_k(r, k),
        f'NDCG@{k}': lambda r: ndcg_at_k(r, k),
        'AP': average_precision,
        'R-Prec': r_precision,
        'MRR': reciprocal_rank,
    }


# ── Tie-aware evaluation ────────────────────────────────────────────────────

def ranked_labels(scores: Sequence[float], labels: Sequence[float], rng: np.random.Generator) -> List[float]:
    """Sort by score desc, breaking ties uniformly at random."""
    jitter = rng.random(len(scores))
    order = sorted(range(len(scores)), key=lambda i: (-scores[i], jitter[i]))
    return [labels[i] for i in order]


def n_tied(scores: Sequence[float]) -> int:
    """Candidates that share their score with at least one other candidate."""
    from collections import Counter
    c = Counter(round(float(s), 9) for s in scores)
    return sum(v for v in c.values() if v > 1)


def evaluate_scores(scores: Sequence[float], labels: Sequence[float], k: int = 5,
                    tie_samples: int = 500, seed: int = 0) -> Dict[str, float]:
    """All metrics, averaged over random tie-breaks (exact if there are no ties)."""
    suite = metric_suite(k)
    rng = np.random.default_rng(seed)
    samples = 1 if n_tied(scores) == 0 else tie_samples
    acc = {name: 0.0 for name in suite}
    for _ in range(samples):
        rels = ranked_labels(scores, labels, rng)
        for name, fn in suite.items():
            acc[name] += fn(rels)
    out = {name: v / samples for name, v in acc.items()}
    out['AUC'] = auc(scores, labels)
    out['ties'] = n_tied(scores)
    return out


# ── Bootstrap (stratified over candidates) ─────────────────────────────────

def stratified_bootstrap(method_scores: Dict[str, Sequence[float]], labels: Sequence[float],
                         k: int = 5, n_boot: int = 2000, seed: int = 42,
                         metrics: Sequence[str] = ('AP', 'NDCG@5', 'P@5', 'AUC'),
                         reference: Optional[str] = None) -> Dict:
    """
    Resample candidates with replacement within each relevance class (so every
    replicate has the same number of relevant / non-relevant candidates), score
    every method on the SAME replicate, and report:
      ci[method][metric]                  95% percentile interval
      diff[method][metric]                mean, 95% CI and two-sided bootstrap p of
                                          (method − reference) — paired
    With one job and a dozen candidates these intervals are wide; that is the
    honest uncertainty of the experiment.
    """
    rng = np.random.default_rng(seed)
    labels = list(labels)
    pos_idx = [i for i, l in enumerate(labels) if l > 0]
    neg_idx = [i for i, l in enumerate(labels) if l <= 0]
    suite = metric_suite(k)
    draws: Dict[str, Dict[str, List[float]]] = {m: {x: [] for x in metrics} for m in method_scores}

    for _ in range(n_boot):
        idx = list(rng.choice(pos_idx, len(pos_idx), replace=True)) + \
              list(rng.choice(neg_idx, len(neg_idx), replace=True))
        lab = [labels[i] for i in idx]
        for m, sc in method_scores.items():
            s = [sc[i] for i in idx]
            rels = ranked_labels(s, lab, rng)
            for x in metrics:
                draws[m][x].append(auc(s, lab) if x == 'AUC' else suite[x](rels))

    def ci(v):
        return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]

    out = {'n_boot': n_boot, 'seed': seed, 'ci': {}, 'diff': {}}
    for m in method_scores:
        out['ci'][m] = {x: ci(draws[m][x]) for x in metrics}
    if reference:
        for m in method_scores:
            if m == reference:
                continue
            out['diff'][m] = {}
            for x in metrics:
                d = np.array(draws[m][x]) - np.array(draws[reference][x])
                p = 2 * min((d <= 0).mean(), (d >= 0).mean())
                out['diff'][m][x] = {'mean': float(d.mean()), 'ci': ci(d), 'p': float(min(1.0, p))}
    return out


# ── Rank correlation and agreement ─────────────────────────────────────────

def kendall_tau(a: Sequence[float], b: Sequence[float]) -> float:
    """Kendall's tau-b between two score vectors over the same candidates."""
    n = len(a)
    conc = disc = ties_a = ties_b = 0
    for i in range(n):
        for j in range(i + 1, n):
            da, db = np.sign(a[i] - a[j]), np.sign(b[i] - b[j])
            if da == 0 and db == 0:
                continue
            if da == 0:
                ties_a += 1
            elif db == 0:
                ties_b += 1
            elif da == db:
                conc += 1
            else:
                disc += 1
    denom = math.sqrt((conc + disc + ties_a) * (conc + disc + ties_b))
    return (conc - disc) / denom if denom else 1.0


def cohens_kappa(a: Sequence, b: Sequence) -> float:
    """Cohen's kappa for two annotators over the same items (nominal labels)."""
    assert len(a) == len(b) and len(a) > 0
    cats = sorted(set(a) | set(b), key=str)
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((list(a).count(c) / n) * (list(b).count(c) / n) for c in cats)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def fleiss_kappa(table: Sequence[Sequence[int]]) -> float:
    """Fleiss' kappa; table[i][j] = raters assigning item i to category j."""
    t = np.asarray(table, dtype=float)
    n_items, _ = t.shape
    raters = t.sum(axis=1)
    if not np.all(raters == raters[0]) or raters[0] < 2:
        raise ValueError('Fleiss kappa needs the same number (≥ 2) of raters per item')
    r = raters[0]
    p_j = t.sum(axis=0) / (n_items * r)
    p_i = ((t ** 2).sum(axis=1) - r) / (r * (r - 1))
    p_bar, pe = p_i.mean(), (p_j ** 2).sum()
    return 1.0 if pe == 1 else (p_bar - pe) / (1 - pe)
