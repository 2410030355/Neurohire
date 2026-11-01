"""python manage.py evaluate --dataset <dir> [--similarity tfidf|gemini] [--out <dir>]"""
import os
import subprocess
from datetime import datetime

import numpy as np
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Evaluate NeuroHire against baselines on a labelled dataset (paper §IV.G).'

    def add_arguments(self, parser):
        parser.add_argument('--dataset', required=True, help='folder with résumés and dataset.json')
        parser.add_argument('--similarity', choices=['tfidf', 'gemini'], default='tfidf',
                            help='representation for SS (gemini needs GEMINI_API_KEY)')
        parser.add_argument('--out', help='output folder (default: evaluation_results/<dataset>_<similarity>)')
        parser.add_argument('--k', type=int, default=5)
        parser.add_argument('--n-boot', type=int, default=2000)
        parser.add_argument('--seed', type=int, default=42)
        parser.add_argument('--gemini-extraction', action='store_true',
                            help='use Gemini for field extraction too (default: deterministic regex)')

    def handle(self, *args, **o):
        import logging
        logging.getLogger('neurohire').setLevel(logging.WARNING)
        from neurohire.evaluation.data import load_dataset
        from neurohire.evaluation.report import write_outputs
        from neurohire.evaluation.runner import evaluate_job
        from neurohire import scoring

        if not os.path.isdir(o['dataset']):
            raise CommandError(f"Dataset folder not found: {o['dataset']}")
        if o['similarity'] == 'gemini' and not os.environ.get('GEMINI_API_KEY'):
            raise CommandError('GEMINI_API_KEY is not set. Use --similarity tfidf or export the key.')

        ds = load_dataset(o['dataset'])
        out = o['out'] or os.path.join('evaluation_results', f"{ds.name}_{o['similarity']}")
        try:
            commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'],
                                             stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            commit = 'unknown'

        jobs = [evaluate_job(ds, job, o['similarity'], o['k'], o['n_boot'], o['seed'],
                             o['gemini_extraction'], progress=self.stdout.write) for job in ds.jobs]

        macro = {}
        for m in jobs[0]['main']:
            macro[m] = {x: float(np.mean([j['main'][m][x] for j in jobs]))
                        for x in ('AP', f"NDCG@{o['k']}", 'AUC')}

        results = {
            'dataset': {'name': ds.name, 'root': ds.root, 'description': ds.description,
                        'n_resumes': len(ds.resumes), 'jobs': [j.id for j in ds.jobs]},
            'config': {
                'similarity (SS)': o['similarity'],
                'extraction': 'gemini+regex' if o['gemini_extraction'] else 'regex (deterministic)',
                'reference date for "Present"': str(ds.reference_date or 'today'),
                'FS weights': f'{scoring.W_SS} / {scoring.W_AS}',
                'VS rule (main)': 'first mention, 60-char window',
                'k': o['k'], 'bootstrap replicates': o['n_boot'], 'seed': o['seed'],
                'code version': commit, 'run at': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
            },
            'jobs': jobs, 'macro': macro,
        }
        for p in write_outputs(results, out, o['k']):
            self.stdout.write(self.style.SUCCESS(f'wrote {p}'))
