"""python manage.py agreement --csv annotations.csv [--write-labels dataset.json]

Input columns: job_id, candidate_id, annotator, label. Reports pairwise Cohen's
kappa, Fleiss' kappa (if every item has the same number of annotators) and
the majority label per item; optionally writes majority labels into a
dataset.json so `evaluate` uses the independent labels.
"""
import csv
import itertools
import json
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Inter-annotator agreement and majority labels.'

    def add_arguments(self, parser):
        parser.add_argument('--csv', required=True)
        parser.add_argument('--label-column', default='label')
        parser.add_argument('--write-labels', help='dataset.json to update with majority labels')

    def handle(self, *args, **o):
        from neurohire.evaluation.metrics import cohens_kappa, fleiss_kappa
        ann = defaultdict(dict)   # annotator -> (job, cand) -> label
        with open(o['csv'], encoding='utf-8') as f:
            for row in csv.DictReader(f):
                col = next((c for c in row if c.startswith(o['label_column'])), None)
                if not col or not row[col].strip():
                    continue
                ann[row['annotator'].strip()][(row['job_id'], row['candidate_id'])] = int(row[col])
        if len(ann) < 2:
            raise CommandError('Need labels from at least two annotators.')

        for a, b in itertools.combinations(sorted(ann), 2):
            items = sorted(set(ann[a]) & set(ann[b]))
            k = cohens_kappa([ann[a][i] for i in items], [ann[b][i] for i in items])
            self.stdout.write(f"Cohen's kappa {a} vs {b}: {k:.3f} on {len(items)} items")

        items = sorted(set.intersection(*(set(v) for v in ann.values())))
        cats = sorted({l for v in ann.values() for l in v.values()})
        table = [[sum(1 for a in ann if ann[a][i] == c) for c in cats] for i in items]
        try:
            self.stdout.write(f"Fleiss' kappa ({len(ann)} annotators, {len(items)} items): {fleiss_kappa(table):.3f}")
        except ValueError as e:
            self.stdout.write(f"Fleiss' kappa not computed: {e}")

        majority, ties = {}, []
        for i in items:
            counts = Counter(ann[a][i] for a in ann).most_common()
            if len(counts) > 1 and counts[0][1] == counts[1][1]:
                ties.append(i)
            majority[i] = counts[0][0]
        self.stdout.write(f'{len(ties)} items without a majority: {ties}' if ties else 'Every item has a majority.')

        if o['write_labels']:
            with open(o['write_labels'], encoding='utf-8') as f:
                spec = json.load(f)
            for job in spec['jobs']:
                job['labels'] = {c: l for (jid, c), l in majority.items() if jid == job['id']}
                job['label_source'] = f'majority of {len(ann)} independent annotators'
            with open(o['write_labels'], 'w', encoding='utf-8') as f:
                json.dump(spec, f, indent=2)
            self.stdout.write(self.style.SUCCESS(f"majority labels written to {o['write_labels']}"))
