"""python manage.py evaluate --dataset <dir> [--similarity tfidf|gemini] [--scheme NAME] [--out <dir>]"""
import os
import subprocess
from datetime import datetime

import numpy as np
from django.core.management.base import BaseCommand, CommandError

MACRO_REFERENCES = ('Keyword (skill overlap)', 'NeuroHire: SS only')


def _strip_private(obj):
    """Drop '_draws' (bootstrap replicates) before writing JSON."""
    if isinstance(obj, dict):
        return {k: _strip_private(v) for k, v in obj.items() if not k.startswith('_')}
    if isinstance(obj, list):
        return [_strip_private(v) for v in obj]
    return obj


def _macro(jobs, key, k):
    """Mean over jobs per bootstrap replicate → macro CIs and paired differences."""
    from neurohire.evaluation.metrics import summarize_draws
    per_job = [j[key] if key == '_draws' else j[key]['_draws'] for j in jobs]
    methods = list(per_job[0])
    draws = {m: {x: list(np.mean([pj[m][x] for pj in per_job], axis=0)) for x in per_job[0][m]}
             for m in methods}
    return summarize_draws(draws, MACRO_REFERENCES)


class Command(BaseCommand):
    help = 'Evaluate NeuroHire against baselines on a labelled dataset (paper §IV.G).'

    def add_arguments(self, parser):
        parser.add_argument('--dataset', required=True, help='folder with résumés and dataset.json')
        parser.add_argument('--similarity', choices=['tfidf', 'gemini'], default='tfidf',
                            help='representation for SS (gemini needs GEMINI_API_KEY)')
        parser.add_argument('--scheme', help='label scheme (default: every scheme the dataset defines)')
        parser.add_argument('--out', help='output folder (default: evaluation_results/<dataset>_<similarity>[_<scheme>])')
        parser.add_argument('--k', type=int, default=5)
        parser.add_argument('--n-boot', type=int, default=2000)
        parser.add_argument('--seed', type=int, default=42)
        parser.add_argument('--gemini-extraction', action='store_true',
                            help='use Gemini for field extraction too (default: deterministic regex)')

    def handle(self, *args, **o):
        import logging
        logging.getLogger('neurohire').setLevel(logging.WARNING)
        from neurohire.evaluation.data import load_dataset, schemes_of
        from neurohire.evaluation.report import write_outputs
        from neurohire.evaluation.runner import evaluate_job
        from neurohire import scoring

        if not os.path.isdir(o['dataset']):
            raise CommandError(f"Dataset folder not found: {o['dataset']}")
        if o['similarity'] == 'gemini' and not os.environ.get('GEMINI_API_KEY'):
            raise CommandError('GEMINI_API_KEY is not set. Use --similarity tfidf or export the key.')
        try:
            schemes = [o['scheme']] if o['scheme'] else schemes_of(o['dataset'])
            datasets = [load_dataset(o['dataset'], s) for s in schemes]   # validate everything first
        except ValueError as e:
            raise CommandError(str(e))
        try:
            commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'],
                                             stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            commit = 'unknown'

        for scheme, ds in zip(schemes, datasets):
            exp = ds.meta.get('experiments', {})
            suffix = f'_{scheme}' if scheme else ''
            if o['out']:
                out = o['out'] if len(schemes) == 1 else f"{o['out']}{suffix}"
            else:
                out = os.path.join('evaluation_results', f"{ds.name}_{o['similarity']}{suffix}")
            self.stdout.write(f"== {ds.name} · {o['similarity']}" + (f' · scheme {scheme}' if scheme else ''))

            jobs = [evaluate_job(ds, job, o['similarity'], o['k'], o['n_boot'], o['seed'],
                                 o['gemini_extraction'], progress=self.stdout.write,
                                 stuffing_sample=exp.get('stuffing_sample'),
                                 fairness_sample=exp.get('fairness_sample')) for job in ds.jobs]

            k = o['k']
            macro = {m: {x: float(np.mean([j['main'][m][x] for j in jobs])) for x in ('AP', f'NDCG@{k}', f'P@{k}', 'AUC')}
                     for m in jobs[0]['main']}
            macro_stuffing = {m: {x: float(np.mean([j['stuffing']['methods'][m][x] for j in jobs]))
                                  for x in ('AP', f'NDCG@{k}', 'AUC')}
                              for m in jobs[0]['stuffing']['methods']}
            results = {
                'dataset': {'name': ds.name, 'root': ds.root, 'description': ds.description,
                            'source': ds.meta.get('source'), 'n_resumes': len(ds.resumes),
                            'jobs': [j.id for j in ds.jobs], 'label_scheme': scheme},
                'config': {
                    'similarity (SS)': o['similarity'],
                    'extraction': 'gemini+regex' if o['gemini_extraction'] else 'regex (deterministic)',
                    'label scheme': scheme or 'labels in dataset',
                    'reference date for "Present"': str(ds.reference_date or 'today'),
                    'FS weights': f'{scoring.W_SS} / {scoring.W_AS}',
                    'VS rule (main)': 'first mention, 60-char window',
                    'k': k, 'bootstrap replicates': o['n_boot'], 'seed': o['seed'],
                    'stuffing sample (non-relevant résumés per job)': exp.get('stuffing_sample') or 'all',
                    'fairness sample (résumés per job)': exp.get('fairness_sample') or 'all',
                    'code version': commit, 'run at': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
                },
                'jobs': jobs, 'macro': macro, 'macro_stuffing': macro_stuffing,
            }
            if len(jobs) > 1:
                results['macro_bootstrap'] = _macro(jobs, '_draws', k)
                results['macro_stuffing_bootstrap'] = _macro([j['stuffing'] for j in jobs], '_draws', k)
            for p in write_outputs(_strip_private(results), out, k):
                self.stdout.write(self.style.SUCCESS(f'wrote {p}'))
