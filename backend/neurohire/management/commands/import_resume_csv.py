"""
python manage.py import_resume_csv --csv UpdatedResumeDataSet.csv --out evaluation_data/kaggle_tech

Turns a public résumé CSV (one résumé per row + a curator-assigned category)
into an evaluation dataset folder:

  resumes/R0001.txt …   one file per UNIQUE résumé (neutral file names)
  categories.csv        id, category, copies_in_source, first_row
  import_report.json    rows read, exact/normalised duplicates removed, per-category counts

Duplicates are removed after whitespace/case normalisation: the same résumé
appearing several times would otherwise inflate every ranking metric.
Mis-decoded UTF-8 ("â€¢" for "•") is repaired.
"""
import csv
import json
import os
import re
from collections import Counter, OrderedDict

from django.core.management.base import BaseCommand, CommandError


def repair_text(s: str) -> str:
    """
    Undo UTF-8 that was decoded as Latin-1 or Windows-1252 ("â€¢" → "•"),
    then normalise whitespace. If neither round-trip is clean the text is left
    as it is — characters are never dropped.
    """
    if any(ord(ch) > 127 for ch in s):
        for enc in ('latin-1', 'cp1252'):
            try:
                s = s.encode(enc).decode('utf-8')
                break
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
    s = s.replace('\r\n', '\n').replace('\r', '\n').replace('\xa0', ' ')
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()


def normalise_key(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip().lower()


class Command(BaseCommand):
    help = 'Import a résumé CSV (text + category) into a deduplicated evaluation dataset folder.'

    def add_arguments(self, parser):
        parser.add_argument('--csv', required=True)
        parser.add_argument('--out', required=True)
        parser.add_argument('--text-col', default='Resume')
        parser.add_argument('--category-col', default='Category')

    def handle(self, *args, **o):
        if not os.path.exists(o['csv']):
            raise CommandError(f"CSV not found: {o['csv']}")
        unique = OrderedDict()   # key -> {text, category, copies, first_row}
        rows = 0
        with open(o['csv'], encoding='utf-8', newline='') as f:
            for i, row in enumerate(csv.DictReader(f)):
                rows += 1
                text = repair_text(row[o['text_col']] or '')
                if not text:
                    continue
                key = normalise_key(text)
                cat = (row[o['category_col']] or '').strip()
                if key in unique:
                    unique[key]['copies'] += 1
                    if unique[key]['category'] != cat:
                        raise CommandError(f'Row {i}: same résumé with two categories '
                                           f"({unique[key]['category']} / {cat}) — resolve before importing.")
                    continue
                unique[key] = {'text': text, 'category': cat, 'copies': 1, 'first_row': i}

        res_dir = os.path.join(o['out'], 'resumes')
        os.makedirs(res_dir, exist_ok=True)
        with open(os.path.join(o['out'], 'categories.csv'), 'w', newline='', encoding='utf-8') as cf:
            w = csv.writer(cf)
            w.writerow(['id', 'category', 'copies_in_source', 'first_row'])
            for n, item in enumerate(unique.values(), start=1):
                rid = f'R{n:04d}'
                with open(os.path.join(res_dir, f'{rid}.txt'), 'w', encoding='utf-8') as rf:
                    rf.write(item['text'] + '\n')
                w.writerow([rid, item['category'], item['copies'], item['first_row']])

        report = {
            'source_csv': os.path.basename(o['csv']), 'rows_read': rows, 'unique_resumes': len(unique),
            'duplicates_removed': rows - len(unique),
            'unique_per_category': dict(sorted(Counter(v['category'] for v in unique.values()).items())),
            'rows_per_category': dict(sorted(Counter(v['category'] for v in unique.values()
                                                     for _ in range(v['copies'])).items())),
        }
        with open(os.path.join(o['out'], 'import_report.json'), 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        self.stdout.write(self.style.SUCCESS(
            f"{rows} rows → {len(unique)} unique résumés ({rows - len(unique)} duplicates removed) in {o['out']}"))
