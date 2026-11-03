"""
python manage.py performance_report --dataset <dir> [--similarity tfidf|gemini] [--gemini-extraction]
                                    [--examples 3] [--out <dir>]

Measures processing time per stage on a dataset (extraction + CS/VS/LV,
embedding/similarity, ranking) and runs robustness cases (empty résumé,
missing fields, empty job description, Gemini API failures). Also writes a
few example résumés with the JSON the app extracts from them.

Writes <out>/performance.md, <out>/performance.json and <out>/examples/.
Timings are measured on the machine that runs the command; report that machine.
"""
import json
import os
import platform
import statistics
import time
from contextlib import contextmanager
from datetime import datetime
from unittest import mock

from django.core.management.base import BaseCommand, CommandError

EXAMPLE_FIELDS = [
    'name', 'email', 'phone', 'skills', 'other_skills', 'jd_skills', 'missing_skills',
    'experience_years', 'experience_years_dated', 'experience_years_claimed', 'experience_source',
    'employment_history', 'projects', 'education', 'consistency_score', 'consistency_flags',
    'consistency_rules_skipped', 'skill_validation_score', 'skill_validation_score_jd',
    'skill_validation_score_original', 'jd_skills_evidenced', 'validated_skills', 'lv_raw',
    'lv_new_skills', 'lv_span_years', 'lv_basis', 'extraction_method',
]


def _stats(xs):
    xs = sorted(xs)
    if not xs:
        return {}
    p95 = xs[min(len(xs) - 1, int(round(0.95 * (len(xs) - 1))))]
    return {'n': len(xs), 'mean_ms': statistics.mean(xs) * 1000, 'median_ms': statistics.median(xs) * 1000,
            'p95_ms': p95 * 1000, 'max_ms': xs[-1] * 1000, 'total_s': sum(xs)}


@contextmanager
def _no_gemini_similarity():
    """Force the TF-IDF path for similarity (as when no API key is set)."""
    with mock.patch('neurohire.analysis_engine._get_gemini_client', return_value=None):
        yield


class _FailingModels:
    def __getattr__(self, name):
        def fail(*a, **k):
            raise RuntimeError('simulated Gemini API failure (HTTP 503)')
        return fail


class _FailingClient:
    models = _FailingModels()


class Command(BaseCommand):
    help = 'Processing-time and robustness report (stage timings, failure cases, extraction examples).'

    def add_arguments(self, parser):
        parser.add_argument('--dataset', required=True)
        parser.add_argument('--similarity', choices=['tfidf', 'gemini'], default='tfidf')
        parser.add_argument('--gemini-extraction', action='store_true',
                            help='also time Gemini structured extraction (needs GEMINI_API_KEY)')
        parser.add_argument('--examples', type=int, default=3, help='résumés to dump with extracted JSON')
        parser.add_argument('--jobs', help='comma-separated job ids (default: all)')
        parser.add_argument('--out')

    def handle(self, *args, **o):
        from neurohire.analysis_engine import analyze_text, get_similarity_batch
        from neurohire.extraction import extract_skills
        from neurohire.ranking import rank_candidates
        from neurohire.evaluation.data import load_dataset
        from neurohire.evaluation.runner import to_candidates

        if o['similarity'] == 'gemini' and not os.environ.get('GEMINI_API_KEY'):
            raise CommandError('--similarity gemini needs GEMINI_API_KEY')
        try:
            ds = load_dataset(o['dataset'])
        except ValueError as e:
            raise CommandError(str(e))
        jobs = ds.jobs
        if o['jobs']:
            want = set(o['jobs'].split(','))
            jobs = [j for j in jobs if j.id in want]
        out = o['out'] or os.path.join('evaluation_results', f'{ds.name}_{o["similarity"]}_performance')
        os.makedirs(os.path.join(out, 'examples'), exist_ok=True)
        ref = ds.reference_date

        # ── 1. Extraction + CS/VS/LV (per résumé, JD-independent part) ──────
        self.stdout.write(f'Analysing {len(ds.resumes)} résumés…')
        job0 = jobs[0]
        analyses, t_extract = {}, []
        for r in ds.resumes:
            t0 = time.perf_counter()
            analyses[r.id] = analyze_text(r.text, job0.title, job0.jd, reference_date=ref,
                                          compute_similarity=False,
                                          use_gemini_extraction=o['gemini_extraction'])
            t_extract.append(time.perf_counter() - t0)

        # ── 2. Similarity (embedding) and 3. ranking, per job ───────────────
        per_job = []
        for job in jobs:
            cands = to_candidates(analyses)
            texts = [c['text'] for c in cands]
            t0 = time.perf_counter()
            if o['similarity'] == 'gemini':
                sim = get_similarity_batch(texts, job.jd)
            else:
                with _no_gemini_similarity():
                    sim = get_similarity_batch(texts, job.jd)
            t_sim = time.perf_counter() - t0
            if o['similarity'] == 'gemini' and sim['method'] != 'gemini':
                raise CommandError(f'Gemini embeddings failed for job {job.id} (fell back to {sim["method"]}).')

            fixed = lambda _texts, _jd, _caches=None, s=sim: s   # ranking only, similarity precomputed
            t0 = time.perf_counter()
            ranked = rank_candidates(cands, job.jd, fixed, extract_skills)
            t_rank = time.perf_counter() - t0
            per_job.append({'job': job.id, 'title': job.title, 'candidates': len(cands),
                            'similarity_method': sim['method'], 'similarity_s': t_sim,
                            'similarity_ms_per_resume': t_sim / len(cands) * 1000,
                            'ranking_s': t_rank, 'ranked': len(ranked['results'])})
            self.stdout.write(f'  {job.id}: similarity {t_sim:.2f}s ({sim["method"]}), ranking {t_rank*1000:.1f} ms')

        # ── 4. Robustness cases ─────────────────────────────────────────────
        rob = self._robustness(analyze_text, get_similarity_batch, rank_candidates, extract_skills,
                               to_candidates, job0, ref)

        # ── 5. Extraction examples ──────────────────────────────────────────
        examples = []
        for r in ds.resumes[:max(0, o['examples'])]:
            a = analyses[r.id]
            with open(os.path.join(out, 'examples', f'{r.id}_resume.txt'), 'w', encoding='utf-8') as f:
                f.write(r.text)
            with open(os.path.join(out, 'examples', f'{r.id}_extracted.json'), 'w', encoding='utf-8') as f:
                json.dump({k: a.get(k) for k in EXAMPLE_FIELDS}, f, indent=2, ensure_ascii=False, default=str)
            examples.append(r.id)

        result = {
            'dataset': ds.name, 'similarity': o['similarity'], 'gemini_extraction': o['gemini_extraction'],
            'run_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
            'machine': {'python': platform.python_version(), 'platform': platform.platform(),
                        'processor': platform.processor() or platform.machine(), 'cpus': os.cpu_count()},
            'extraction': _stats(t_extract), 'jobs': per_job, 'robustness': rob, 'examples': examples,
        }
        with open(os.path.join(out, 'performance.json'), 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        with open(os.path.join(out, 'performance.md'), 'w', encoding='utf-8') as f:
            f.write(self._markdown(result))
        self.stdout.write(self.style.SUCCESS(f'Wrote {out}/performance.md'))

    # ------------------------------------------------------------------
    def _robustness(self, analyze_text, get_similarity_batch, rank_candidates, extract_skills,
                    to_candidates, job, ref):
        normal = ("Software Engineer, Acme Corp (Jan 2019 - Dec 2022)\n"
                  "Developed REST APIs in Java and Spring Boot. Built CI/CD pipelines with Jenkins and Docker.\n"
                  "Skills: Java, Spring Boot, Docker, Jenkins, SQL")
        cases = [
            ('Empty résumé', '', job.jd, {}),
            ('Whitespace-only résumé', '   \n\t ', job.jd, {}),
            ('No skills, no dates, no contact details', 'I am a hard-working person who likes computers.', job.jd, {}),
            ('Skills but no dated experience', 'Skills: Java, Python, SQL, Docker', job.jd, {}),
            ('Normal résumé, no job description (target role only)', normal, '', {}),
            ('Gemini embedding API failure', normal, job.jd, {'embed_fail': True}),
            ('Gemini extraction API failure', normal, job.jd, {'extract_fail': True}),
        ]
        rows = []
        for label, text, jd, opt in cases:
            row = {'case': label}
            try:
                patches = []
                if opt.get('embed_fail'):
                    patches.append(mock.patch('neurohire.analysis_engine._get_gemini_client',
                                              return_value=_FailingClient()))
                else:
                    patches.append(mock.patch('neurohire.analysis_engine._get_gemini_client', return_value=None))
                if opt.get('extract_fail'):
                    patches += [mock.patch('neurohire.extraction.GEMINI_EXTRACTION_ENABLED', True),
                                mock.patch('neurohire.extraction.get_gemini_client', return_value=_FailingClient())]
                for p in patches:
                    p.start()
                try:
                    a = analyze_text(text, job.title, jd, reference_date=ref,
                                     use_gemini_extraction=bool(opt.get('extract_fail')))
                    cand = to_candidates({'x': a})
                    ranked = rank_candidates(cand, jd, get_similarity_batch, extract_skills)
                    r = ranked['results'][0] if ranked['results'] else {}
                finally:
                    for p in patches:
                        p.stop()
                row.update({
                    'outcome': 'handled (scored)',
                    'similarity_method': a['similarity_method'], 'extraction_method': a['extraction_method'],
                    'SS': a['semantic_score'], 'CS': a['consistency_score'], 'VS': a['skill_validation_score'],
                    'LV': a['lv_score'], 'AS': a['analytical_score'], 'FS': a['final_score'],
                    'missing_components': a['missing_components'],
                    'ranking_FS': r.get('final_score'),
                })
            except ValueError as e:
                row.update({'outcome': f'rejected: {e} (upload API returns HTTP 400)'})
            except Exception as e:  # anything else is a robustness failure — report it
                row.update({'outcome': f'ERROR {type(e).__name__}: {e}'})
            rows.append(row)
        return rows

    def _markdown(self, r):
        f = lambda v, d=1: '—' if v is None else (f'{v:.{d}f}' if isinstance(v, (int, float)) else str(v))
        m = r['machine']
        L = [f'# Performance and robustness — {r["dataset"]}', '',
             f'Run {r["run_at"]} · similarity `{r["similarity"]}` · Gemini extraction '
             f'`{"on" if r["gemini_extraction"] else "off"}`  ',
             f'Machine: {m["platform"]}, {m["cpus"]} CPUs, Python {m["python"]}. '
             'Times include no network for TF-IDF; Gemini times include API latency.', '',
             '## 1. Processing time per stage', '']
        e = r['extraction']
        L += ['| Stage | n | mean | median | p95 | max | total |', '|---|---|---|---|---|---|---|',
              f'| Extraction + CS/VS/LV (per résumé) | {e["n"]} | {f(e["mean_ms"])} ms | {f(e["median_ms"])} ms | '
              f'{f(e["p95_ms"])} ms | {f(e["max_ms"])} ms | {f(e["total_s"], 2)} s |', '']
        L += ['| Job | candidates | similarity method | similarity (embedding) time | per résumé | ranking time |',
              '|---|---|---|---|---|---|']
        for j in r['jobs']:
            L.append(f'| {j["title"]} | {j["candidates"]} | {j["similarity_method"]} | {f(j["similarity_s"], 2)} s | '
                     f'{f(j["similarity_ms_per_resume"])} ms | {f(j["ranking_s"] * 1000)} ms |')
        L += ['', 'Ranking time excludes similarity (measured separately) and covers LV normalisation, '
              'JD-conditioned VS, AS/FS and sorting.', '',
              '## 2. Robustness cases', '',
              '| Case | Outcome | SS method | Extraction | SS | CS | VS | LV | AS | FS | missing |',
              '|---|---|---|---|---|---|---|---|---|---|---|']
        for c in r['robustness']:
            L.append(f'| {c["case"]} | {c["outcome"]} | {c.get("similarity_method", "—")} | '
                     f'{c.get("extraction_method", "—")} | {f(c.get("SS"))} | {f(c.get("CS"))} | {f(c.get("VS"))} | '
                     f'{f(c.get("LV"))} | {f(c.get("AS"))} | {f(c.get("FS"))} | '
                     f'{", ".join(c.get("missing_components") or []) or "—"} |')
        L += ['', '"—" = not applicable / not available (never replaced by 0). API failures are simulated '
              'by a client that raises on every call.', '',
              '## 3. Extraction examples', '',
              'See `examples/<id>_resume.txt` (input) and `examples/<id>_extracted.json` (output): '
              + ', '.join(r['examples']), '']
        return '\n'.join(L)
