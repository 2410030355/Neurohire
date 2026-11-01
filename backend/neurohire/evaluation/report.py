"""Write evaluation results as Markdown (for the paper), JSON and CSV."""
from __future__ import annotations

import csv
import json
import os
from typing import Dict, List


def _f(v, nd=2):
    if v is None:
        return '—'
    try:
        if v != v:  # NaN
            return '—'
        return f'{v:.{nd}f}'
    except (TypeError, ValueError):
        return str(v)


def _table(headers: List[str], rows: List[List]) -> str:
    out = ['| ' + ' | '.join(headers) + ' |', '|' + '|'.join('---' for _ in headers) + '|']
    out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return '\n'.join(out)


def _ci(ci):
    return f'[{_f(ci[0])}, {_f(ci[1])}]' if ci else ''


def job_markdown(r: Dict, k: int) -> str:
    j, main, boot = r['job'], r['main'], r['bootstrap']
    lines = [f"## Job: {j['title']} (`{j['id']}`)",
             f"{j['n']} candidates, {j['n_relevant']} labelled relevant.",
             '', f"**Job description.** {j['jd']}", '']
    if j.get('jd_note'):
        lines += [f"*JD provenance:* {j['jd_note']}", '']
    if r.get('cs_constant'):
        lines += ['> **Note:** CS is identical for every candidate in this pool, so adding CS cannot change '
                  'the ranking here (the SS and SS+CS rows must coincide).', '']

    lines += ['### 1. Ranking quality (95% stratified-bootstrap CI)', '']
    rows = []
    for m, e in main.items():
        ci = boot['ci'].get(m, {})
        rows.append([m, _f(e[f'P@{k}']), _f(e[f'R@{k}']), _f(e[f'NDCG@{k}']),
                     f"{_f(e['AP'])} {_ci(ci.get('AP'))}", _f(e['R-Prec']), _f(e['MRR']),
                     f"{_f(e['AUC'])} {_ci(ci.get('AUC'))}", e['ties']])
    lines += [_table(['Method', f'P@{k}', f'R@{k}', f'NDCG@{k}', 'AP [95% CI]', 'R-Prec', 'MRR',
                      'AUC [95% CI]', 'tied'], rows), '',
              'Ties are resolved by averaging over random tie-breaks (not input order).', '']

    lines += ['### 2. Paired difference vs Keyword (skill overlap)', '']
    rows = []
    for m, d in boot['diff'].items():
        rows.append([m] + [f"{_f(d[x]['mean'], 3)} {_ci(d[x]['ci'])} (p={_f(d[x]['p'], 3)})"
                           for x in ('AP', f'NDCG@{k}', 'AUC')])
    lines += [_table(['Method', 'ΔAP', f'ΔNDCG@{k}', 'ΔAUC'], rows), '',
              'Δ = method − keyword baseline on the same bootstrap replicate; p is a two-sided bootstrap p-value.', '']

    lines += ['### 3. FS weight sensitivity (full model)', '']
    rows = [[_f(w['w_ss'], 1), _f(w['w_as'], 1), _f(w['AP']), _f(w[f'NDCG@{k}']), _f(w['AUC']),
             _f(w['E_AP']), _f(w[f'E_NDCG@{k}']), _f(w['E_AUC'])] for w in r['weights']]
    lines += [_table(['w_SS', 'w_AS', 'AP', f'NDCG@{k}', 'AUC', 'AP (E)', f'NDCG@{k} (E)', 'AUC (E)'], rows), '',
              '(E) = NeuroHire-E, JD-conditioned evidence in place of VS.', '']

    lines += ['### 4. Skill-evidence rule: first mention (paper) vs any mention', '']
    rows = [[m, _f(e['mean_VS'], 1), _f(e['AP']), _f(e[f'NDCG@{k}']), _f(e['AUC'])] for m, e in r['evidence'].items()]
    lines += [_table(['VS rule', 'mean VS', 'AP', f'NDCG@{k}', 'AUC'], rows), '']

    s = r['stuffing']
    lines += ['### 5. Keyword-stuffing robustness', '',
              f"Each of the {s['n_stuffed']} non-relevant résumés was copied with the JD's skills "
              f"({', '.join(s['stuffed_skills'])}) appended to its skills list and no supporting experience. "
              'Copies are labelled not relevant and added to the pool.', '']
    rows = [[m, _f(e['AP']), _f(e[f'NDCG@{k}']), _f(e[f'P@{k}']), _f(e['AUC']), e[f'stuffed_in_top{k}'],
             _f(e['mean_rank_gain'], 1), _f(e['mean_score_gain_pct'], 1)]
            for m, e in s['methods'].items()]
    lines += [_table(['Method', 'AP', f'NDCG@{k}', f'P@{k}', 'AUC', f'stuffed in top {k}',
                      'mean rank gain', 'mean score gain %'], rows), '']

    sb = s.get('bootstrap_vs_ss_only')
    if sb:
        rows = [[m, f"{_f(e['AP'])} {_ci(sb['ci'][m]['AP'])}"] +
                ([f"{_f(sb['diff'][m]['AP']['mean'], 3)} {_ci(sb['diff'][m]['AP']['ci'])} (p={_f(sb['diff'][m]['AP']['p'], 3)})"]
                 if m in sb['diff'] else ['(reference)'])
                for m, e in s['methods'].items()]
        lines += ['Stuffed pool, 95% CIs and paired difference vs *NeuroHire: SS only* '
                  '(does evidence add robustness beyond semantic similarity?):', '',
                  _table(['Method', 'AP [95% CI]', 'ΔAP vs SS only [95% CI] (p)'], rows), '']

    lines += ['### 6. Counterfactual fairness (name swaps)', '',
              'Each résumé re-scored with 8 substituted identities (gender × community); other candidates unchanged.', '']
    rows = []
    for mode, f in r['fairness'].items():
        rows.append([mode, _f(f['mean_abs_dFS'], 3), _f(f['max_abs_dFS'], 3), f['max_abs_rank_change'],
                     _f(f['share_rank_changed'] * 100, 1) + '%', _f(f['gender_gap_mean_FS'], 3)])
    lines += [_table(['Similarity input', 'mean |ΔFS|', 'max |ΔFS|', 'max |Δrank|', 'swaps changing rank',
                      'female − male mean FS'], rows), '']

    lk = r['leakage']
    lines += ['### 7. Label-leakage check', '',
              f"Leaving the \"Ground Truth Label\" line in the text changes SS by {_f(lk['mean_SS_change_if_label_left_in'])} "
              f"points on average (max {_f(lk['max_SS_change_if_label_left_in'])}). {lk['note']}", '']

    lines += ['### 8. Per-candidate scores (full model)', '']
    rows = [[c['id'], c['label'], c['rank_full'], _f(c['FS'], 1), _f(c['SS'], 1), _f(c['CS'], 0), _f(c['VS'], 1),
             _f(c['LV'], 1), _f(c['AS'], 1), _f(c['VS_JD'], 1), c['rank_E'], _f(c['FS_E'], 1),
             _f(c['experience_dated'], 1), _f(c['experience_claimed'], 1), c['n_skills']]
            for c in sorted(r['per_candidate'], key=lambda c: c['rank_full'])]
    lines += [_table(['Candidate', 'label', 'rank', 'FS', 'SS', 'CS', 'VS', 'LV', 'AS', 'VS_JD', 'rank (E)', 'FS (E)',
                      'yrs (dates)', 'yrs (claimed)', '#skills'], rows), '']
    return '\n'.join(lines)


def write_outputs(results: Dict, out_dir: str, k: int) -> List[str]:
    os.makedirs(out_dir, exist_ok=True)
    paths = []

    p = os.path.join(out_dir, 'results.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    paths.append(p)

    for jr in results['jobs']:
        p = os.path.join(out_dir, f"per_candidate_{jr['job']['id']}.csv")
        rows = jr['per_candidate']
        with open(p, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        paths.append(p)

    cfg = results['config']
    md = [f"# NeuroHire evaluation — {results['dataset']['name']}", '',
          _table(['Setting', 'Value'], [[k_, f'`{v}`'] for k_, v in cfg.items()]), '']
    if results['dataset'].get('description'):
        md += [results['dataset']['description'], '']
    for jr in results['jobs']:
        md += [job_markdown(jr, k), '']
    if len(results['jobs']) > 1:
        md += ['## Macro average over jobs', '', _table(
            ['Method', 'mean AP', f'mean NDCG@{k}', 'mean AUC'],
            [[m, _f(v['AP']), _f(v[f'NDCG@{k}']), _f(v['AUC'])] for m, v in results['macro'].items()]), '']
    p = os.path.join(out_dir, 'report.md')
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))
    paths.append(p)
    return paths
