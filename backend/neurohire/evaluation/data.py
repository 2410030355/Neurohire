"""
Evaluation datasets.

A dataset is a folder with résumés (.docx / .pdf / .txt) and a dataset.json:

    {
      "name": "frontend_12",
      "description": "...",
      "reference_date": "2026-01-01",          # 'today' for "Present" (reproducibility)
      "jobs": [
        {
          "id": "frontend",
          "title": "Frontend Developer",
          "jd_file": "jd_frontend.txt",
          "jd_note": "how the JD was obtained",
          "labels": {"Candidate_01_Arjun_Sharma": 1, ...}   # optional
        }
      ]
    }

Labels, in order of precedence:
  1. "labels": {resume_id: 0/1}
  2. "relevant_categories": {"strict": [...], "lenient": [...]} together with a
     categories file (resume_id → category, e.g. from a public dataset's
     curators): relevant = the résumé's category is in the scheme's list
  3. each résumé's "Ground Truth Label: <n> — reason" line
The label line is ALWAYS removed from the text before scoring.
More jobs can share the same résumé pool (multi-role benchmark).

Multi-role example (dataset.json):
    "categories_file": "categories.csv",          # columns: id, category
    "label_schemes": ["strict", "lenient"],
    "jobs": [{"id": "java", "title": "Java Developer", "jd_file": "jd/java.txt",
              "source": {"employer": "...", "url": "...", "accessed": "YYYY-MM-DD"},
              "relevant_categories": {"strict": ["Java Developer"], "lenient": [...]}}]
"""
from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

LABEL_LINE = re.compile(r'^\s*ground[\s_-]*truth(?:[\s_-]*label)?\s*[:\-–—]\s*(\d+)\s*(?:[—–-]\s*(.*))?$',
                        re.IGNORECASE | re.MULTILINE)


@dataclass
class Resume:
    id: str
    path: str
    text: str                       # label line removed
    embedded_label: Optional[int] = None
    embedded_note: str = ''
    category: Optional[str] = None


@dataclass
class Job:
    id: str
    title: str
    jd: str
    labels: Dict[str, int]
    jd_note: str = ''
    source: Dict = field(default_factory=dict)
    scheme: Optional[str] = None
    relevant_categories: List[str] = field(default_factory=list)


@dataclass
class Dataset:
    name: str
    root: str
    resumes: List[Resume]
    jobs: List[Job]
    reference_date: Optional[date] = None
    description: str = ''
    meta: Dict = field(default_factory=dict)
    scheme: Optional[str] = None

    def resume(self, rid: str) -> Resume:
        return next(r for r in self.resumes if r.id == rid)


def read_text(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == '.txt':
        with open(path, encoding='utf-8') as f:
            return f.read()
    if ext in ('.docx', '.pdf'):
        from neurohire.analysis_engine import extract_text_from_pdf
        return extract_text_from_pdf(path)[1]
    raise ValueError(f'Unsupported résumé file: {path}')


def split_label(text: str):
    """(text without the label line, label or None, note)."""
    m = LABEL_LINE.search(text)
    if not m:
        return text, None, ''
    clean = (text[:m.start()] + text[m.end():]).strip()
    return clean, int(m.group(1)), (m.group(2) or '').strip()


def schemes_of(root: str) -> List[Optional[str]]:
    """Label schemes a dataset defines ([None] if it has plain labels)."""
    with open(os.path.join(root, 'dataset.json'), encoding='utf-8') as f:
        spec = json.load(f)
    return list(spec.get('label_schemes') or [None])


def load_dataset(root: str, scheme: Optional[str] = None) -> Dataset:
    with open(os.path.join(root, 'dataset.json'), encoding='utf-8') as f:
        spec = json.load(f)

    categories = {}
    if spec.get('categories_file'):
        with open(os.path.join(root, spec['categories_file']), encoding='utf-8') as f:
            categories = {row['id']: row['category'] for row in csv.DictReader(f)}

    resume_dir = os.path.join(root, spec.get('resume_dir', '.'))
    resumes = []
    for name in sorted(os.listdir(resume_dir)):
        stem, ext = os.path.splitext(name)
        if ext.lower() not in ('.docx', '.pdf', '.txt') or name.startswith(('jd', '~$')):
            continue
        raw = read_text(os.path.join(resume_dir, name))
        clean, label, note = split_label(raw)
        resumes.append(Resume(stem, os.path.join(resume_dir, name), clean, label, note, categories.get(stem)))
    if not resumes:
        raise ValueError(f'No résumés found in {resume_dir}')
    if categories:
        missing = [r.id for r in resumes if r.category is None]
        if missing:
            raise ValueError(f'No category for {missing[:5]}… in {spec["categories_file"]}')

    schemes = spec.get('label_schemes')
    if schemes:
        scheme = scheme or schemes[0]
        if scheme not in schemes:
            raise ValueError(f'Unknown label scheme {scheme!r}; dataset defines {schemes}')

    jobs = []
    for j in spec['jobs']:
        jd_path = os.path.join(root, j['jd_file'])
        if not os.path.exists(jd_path):
            raise ValueError(f"Job {j['id']}: job description file missing: {jd_path}")
        with open(jd_path, encoding='utf-8') as f:
            jd = f.read().strip()
        if len(jd) < 50:
            raise ValueError(f"Job {j['id']}: job description in {jd_path} is empty or too short — "
                             'paste the posting text into it.')
        relevant: List[str] = []
        if j.get('labels'):
            labels = j['labels']
        elif j.get('relevant_categories'):
            if not categories:
                raise ValueError('relevant_categories needs a categories_file')
            relevant = j['relevant_categories'][scheme]
            unknown = set(relevant) - set(categories.values())
            if unknown:
                raise ValueError(f"Job {j['id']}: categories not in the data: {sorted(unknown)}")
            labels = {r.id: int(r.category in relevant) for r in resumes}
        else:
            labels = {r.id: r.embedded_label for r in resumes if r.embedded_label is not None}
        missing = [r.id for r in resumes if r.id not in labels]
        if missing:
            raise ValueError(f"Job {j['id']}: no label for {missing}")
        jobs.append(Job(j['id'], j.get('title', j['id']), jd, {k: int(v) for k, v in labels.items()},
                        j.get('jd_note', ''), j.get('source', {}), scheme, relevant))

    ref = spec.get('reference_date')
    return Dataset(spec.get('name', os.path.basename(root)), root, resumes, jobs,
                   date.fromisoformat(ref) if ref else None, spec.get('description', ''), spec, scheme)
