"""
Controlled perturbations of résumé text for robustness and fairness tests.

skill_stuff()      evidence-aware test: append the JD's skills to a résumé's
                   skills list WITHOUT any supporting experience text. A ranking
                   that rewards bare keyword lists will promote these copies.
swap_identity()    counterfactual fairness test: replace the candidate's name
                   (and the e-mail derived from it) with names associated with a
                   different gender / community; scores should not move.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

_SKILLS_HEADING = re.compile(r'^\s*(?:technical\s+)?skills\s*:?\s*$', re.IGNORECASE)

# Counterfactual identities: (group, first, last). Balanced by gender and by
# commonly perceived community; only used to test that scores do not change.
COUNTERFACTUAL_NAMES: List[Tuple[str, str, str]] = [
    ('male / north', 'Rohit', 'Verma'),
    ('female / north', 'Neha', 'Verma'),
    ('male / south', 'Venkatesh', 'Iyer'),
    ('female / south', 'Lakshmi', 'Iyer'),
    ('male / muslim', 'Imran', 'Qureshi'),
    ('female / muslim', 'Ayesha', 'Qureshi'),
    ('male / christian', 'Joseph', 'Mathew'),
    ('female / christian', 'Mary', 'Mathew'),
]


def skill_stuff(text: str, skills: List[str]) -> str:
    """Add skills to the skills line (or a new SKILLS block if none exists)."""
    lines = text.splitlines()
    addition = '  •  '.join(s for s in skills)
    for i, line in enumerate(lines):
        if _SKILLS_HEADING.match(line):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                lines[j] = lines[j].rstrip() + '  •  ' + addition
                return '\n'.join(lines)
    return text.rstrip() + '\n\nSKILLS\n' + addition + '\n'


def display_names(skills: List[str]) -> List[str]:
    nice = {'react': 'React', 'vue': 'Vue.js', 'typescript': 'TypeScript', 'javascript': 'JavaScript',
            'redux': 'Redux', 'graphql': 'GraphQL', 'jest': 'Jest', 'cypress': 'Cypress',
            'rest api': 'REST API', 'ci/cd': 'CI/CD', 'css': 'CSS', 'responsive design': 'Responsive Design'}
    return [nice.get(s, s.title()) for s in skills]


def original_name(text: str) -> str:
    """The résumé's first non-empty line (the name in these files)."""
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ''


def swap_identity(text: str, first: str, last: str) -> str:
    """Replace the name (full, first and last parts) and name-based e-mail."""
    name = original_name(text)
    parts = name.split()
    out = text
    if name:
        out = re.sub(re.escape(name), f'{first} {last}', out)
    if len(parts) >= 2:
        out = re.sub(rf'\b{re.escape(parts[0])}\b', first, out)
        out = re.sub(rf'\b{re.escape(parts[-1])}\b', last, out)
    out = re.sub(r'\b[A-Za-z0-9._%+-]+@', f'{first.lower()}.{last.lower()}@', out)
    return out


def identity_variants(text: str) -> Dict[str, str]:
    return {f'{g}: {f} {l}': swap_identity(text, f, l) for g, f, l in COUNTERFACTUAL_NAMES}
