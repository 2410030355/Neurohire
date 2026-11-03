"""python manage.py annotation_sheet --dataset <dir> [--out sheet.csv]

Blank labelling sheet for INDEPENDENT annotators: résumé text without the
author's label, one row per (job, candidate), shuffled with a fixed seed so
annotators don't see the author's ordering.
"""
import csv
import random

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create a blank relevance-labelling sheet for independent annotators.'

    def add_arguments(self, parser):
        parser.add_argument('--dataset', required=True)
        parser.add_argument('--out', default='annotation_sheet.csv')
        parser.add_argument('--seed', type=int, default=7)

    def handle(self, *args, **o):
        from neurohire.evaluation.data import load_dataset
        ds = load_dataset(o['dataset'])
        rows = [{'job_id': j.id, 'job_title': j.title, 'job_description': j.jd, 'candidate_id': r.id,
                 'resume_text': r.text, 'annotator': '', 'label (0 = not relevant, 1 = relevant)': '',
                 'confidence (1-3)': '', 'comment': ''}
                for j in ds.jobs for r in ds.resumes]
        random.Random(o['seed']).shuffle(rows)
        with open(o['out'], 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        self.stdout.write(self.style.SUCCESS(f"wrote {o['out']} ({len(rows)} rows)"))
