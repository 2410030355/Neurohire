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

Labels: from "labels" if given, otherwise read from each résumé's
"Ground Truth Label: <n> — reason" line. That line is ALWAYS removed from the
text before scoring (analysis_engine strips it again as a safeguard).
More jobs can share the same résumé pool (multi-role benchmark).
"""
from __future__ import annotations

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


@dataclass
class Job:
    id: str
    title: str
    jd: str
    labels: Dict[str, int]
    jd_note: str = ''


@dataclass
class Dataset:
    name: str
    root: str
    resumes: List[Resume]
    jobs: List[Job]
    reference_date: Optional[date] = None
    description: str = ''
    meta: Dict = field(default_factory=dict)

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


def load_dataset(root: str) -> Dataset:
    with open(os.path.join(root, 'dataset.json'), encoding='utf-8') as f:
        spec = json.load(f)

    resumes = []
    for name in sorted(os.listdir(root)):
        stem, ext = os.path.splitext(name)
        if ext.lower() not in ('.docx', '.pdf', '.txt') or name.startswith(('jd', '~$')):
            continue
        raw = read_text(os.path.join(root, name))
        clean, label, note = split_label(raw)
        resumes.append(Resume(stem, os.path.join(root, name), clean, label, note))
    if not resumes:
        raise ValueError(f'No résumés found in {root}')

    jobs = []
    for j in spec['jobs']:
        with open(os.path.join(root, j['jd_file']), encoding='utf-8') as f:
            jd = f.read().strip()
        labels = j.get('labels') or {r.id: r.embedded_label for r in resumes if r.embedded_label is not None}
        missing = [r.id for r in resumes if r.id not in labels]
        if missing:
            raise ValueError(f"Job {j['id']}: no label for {missing}")
        jobs.append(Job(j['id'], j.get('title', j['id']), jd, {k: int(v) for k, v in labels.items()},
                        j.get('jd_note', '')))

    ref = spec.get('reference_date')
    return Dataset(spec.get('name', os.path.basename(root)), root, resumes, jobs,
                   date.fromisoformat(ref) if ref else None, spec.get('description', ''), spec)
