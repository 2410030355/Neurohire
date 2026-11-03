"""
python manage.py import_resume_csv --csv UpdatedResumeDataSet.csv --out evaluation_data/kaggle_tech

Turns a public résumé CSV (one résumé per row + a curator-assigned category)
into an evaluation dataset folder:

  resumes/R0001.txt …   one file per UNIQUE résumé (neutral file names)
  categories.csv        id, category, copies_in_source, first_row
  import_report.json    rows read, exact/normalised duplicates removed, per-category counts

If <out>/resumes_manifest.json exists (committed for kaggle_tech), the import
is checked against it BEFORE anything is written: same source CSV, same 166
IDs and categories, byte-identical résumé files. A mismatch writes nothing.
--write-manifest creates the manifest from the current import.

Duplicates are removed after whitespace/case normalisation: the same résumé
appearing several times would otherwise inflate every ranking metric.
Mis-decoded UTF-8 ("â€¢" for "•") is repaired.
"""
import csv
import hashlib
import io
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


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    with open(path, 'rb') as f:
        return sha256_bytes(f.read())


MANIFEST = 'resumes_manifest.json'


def normalise_key(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip().lower()


class Command(BaseCommand):
    help = 'Import a résumé CSV (text + category) into a deduplicated evaluation dataset folder.'

    def add_arguments(self, parser):
        parser.add_argument('--csv', required=True)
        parser.add_argument('--out', required=True)
        parser.add_argument('--text-col', default='Resume')
        parser.add_argument('--category-col', default='Category')
        parser.add_argument('--write-manifest', action='store_true',
                            help=f'write {MANIFEST} (SHA-256 of the source CSV and every output file)')

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

        # Build every output in memory first, so it can be verified before writing.
        files = {}
        cat_buf = io.StringIO(newline='')
        w = csv.writer(cat_buf)
        w.writerow(['id', 'category', 'copies_in_source', 'first_row'])
        for n, item in enumerate(unique.values(), start=1):
            rid = f'R{n:04d}'
            files[f'resumes/{rid}.txt'] = (item['text'] + '\n').encode('utf-8')
            w.writerow([rid, item['category'], item['copies'], item['first_row']])
        files['categories.csv'] = cat_buf.getvalue().encode('utf-8')

        source_sha = sha256_file(o['csv'])
        manifest_path = os.path.join(o['out'], MANIFEST)
        source_name = os.path.basename(o['csv'])
        if os.path.exists(manifest_path) and not o['write_manifest']:
            with open(manifest_path, encoding='utf-8') as f:
                m = json.load(f)
            if m.get('source_csv_sha256') == source_sha:      # same file, maybe renamed by a download
                source_name = m.get('source_csv_name', source_name)
        report = {
            'source_csv': source_name, 'rows_read': rows, 'unique_resumes': len(unique),
            'duplicates_removed': rows - len(unique),
            'unique_per_category': dict(sorted(Counter(v['category'] for v in unique.values()).items())),
            'rows_per_category': dict(sorted(Counter(v['category'] for v in unique.values()
                                                     for _ in range(v['copies'])).items())),
        }
        files['import_report.json'] = json.dumps(report, indent=2).encode('utf-8')

        if os.path.exists(manifest_path) and not o['write_manifest']:
            self._verify(manifest_path, source_sha, files)

        os.makedirs(os.path.join(o['out'], 'resumes'), exist_ok=True)
        for rel, data in files.items():
            with open(os.path.join(o['out'], rel), 'wb') as f:
                f.write(data)
        if o['write_manifest']:
            manifest = {
                'description': 'SHA-256 of the source CSV and of every file import_resume_csv writes. '
                               'The résumé texts are not committed; this manifest proves a restore is exact.',
                'source_csv_name': source_name, 'source_csv_sha256': source_sha, 'resume_count': len(unique),
                'files': {rel: sha256_bytes(data) for rel, data in sorted(files.items())},
            }
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
                f.write('\n')
            self.stdout.write(f'Wrote {manifest_path}')
        self.stdout.write(self.style.SUCCESS(
            f"{rows} rows → {len(unique)} unique résumés ({rows - len(unique)} duplicates removed) in {o['out']}"))

    def _verify(self, manifest_path, source_sha, files):
        with open(manifest_path, encoding='utf-8') as f:
            m = json.load(f)
        problems = []
        if m.get('source_csv_sha256') != source_sha:
            problems.append(f"source CSV checksum differs (expected {m.get('source_csv_sha256', '?')[:12]}…, "
                            f'got {source_sha[:12]}…) — a different version of the CSV')
        expected = m.get('files', {})
        got = {rel: sha256_bytes(data) for rel, data in files.items()}
        missing = sorted(set(expected) - set(got))
        extra = sorted(set(got) - set(expected))
        changed = sorted(rel for rel in set(expected) & set(got) if expected[rel] != got[rel])
        if missing:
            problems.append(f'{len(missing)} expected file(s) not produced, e.g. {missing[:3]}')
        if extra:
            problems.append(f'{len(extra)} unexpected file(s), e.g. {extra[:3]}')
        if changed:
            problems.append(f'{len(changed)} file(s) with different content, e.g. {changed[:3]}')
        if problems:
            raise CommandError('Import does not match ' + MANIFEST + '; nothing was written.\n  - '
                               + '\n  - '.join(problems))
        self.stdout.write(self.style.SUCCESS(
            f"Verified against {MANIFEST}: source CSV and all {m.get('resume_count')} résumés, "
            'categories.csv and import_report.json are identical.'))
