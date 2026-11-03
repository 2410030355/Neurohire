"""
scoring.py — NeuroHire candidate assessment, implemented exactly as specified
in the paper (§IV.C–E). Pure functions, no network or database access.

    SS  semantic similarity      cosine(e_r, e_j) × 100                    (C.2)
    CS  consistency score        100 − Σ deductions, three rules           (D.1)
    VS  skill validation score   V / N × 100                               (D.2)
    LV  learning velocity        N_new / Δt, min–max normalised            (D.3)
    AS  analytical score         mean(CS, VS, LV)                          (E.1)
    FS  final score              0.6·SS + 0.4·AS                           (E.2)

Scales: every component is reported on 0–100 before aggregation. LV is
min–max normalised to [0, 1] (as in the paper) and multiplied by 100 so that it
is commensurate with CS and VS.

Missing values (paper §III.E.4: missing information must not be read as low
suitability): a component that cannot be computed is None, never 0.
  * VS is None when no skills are recognised (N = 0).
  * LV is None without ≥ 2 dated positions that mention skills.
  * CS rules that need experience are skipped when experience is unknown.
  * AS is the mean of the components that are available; FS uses SS alone
    when AS is unavailable. Every result lists what was missing.
"""
from __future__ import annotations

import os
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# ── Configured constants (paper values; overridable for sensitivity analysis) ──
W_SS = _env_float('SCORE_WEIGHT_SS', 0.6)          # FS weight of SS
W_AS = _env_float('SCORE_WEIGHT_AS', 0.4)          # FS weight of AS
LV_RAW_MIN_REF = _env_float('LV_RAW_MIN', 0.0)     # reference bounds used when no
LV_RAW_MAX_REF = _env_float('LV_RAW_MAX', 4.0)     # candidate set is available
LV_MIN_SPAN_YEARS = 0.5                            # Δt floor (avoids division blow-up)
VS_WINDOW_CHARS = 60                               # characters each side of the mention
# 'first'    (paper §IV.D.2): only the first mention's ±60-char window is checked.
# 'any'      a verb near ANY mention counts — a skills list at the top of the
#            résumé then no longer hides evidence written further down.
# 'sentence' a verb in the same line/bullet as ANY mention (no window crossing
#            into the next line); used by the JD-conditioned evidence score.
VS_EVIDENCE_MODE = os.environ.get('VS_EVIDENCE_MODE', 'first').strip().lower()

FIT_HIGH, FIT_MEDIUM = 70.0, 40.0                  # final-fit thresholds


# ════════════════════════════════════════════════════════════════════════════
# C. Semantic similarity
# ════════════════════════════════════════════════════════════════════════════

def similarity_to_score(cosine: float) -> float:
    """SS on 0–100: cosine × 100, clipped (negative cosine → 0)."""
    return round(min(100.0, max(0.0, float(cosine) * 100.0)), 2)


# ════════════════════════════════════════════════════════════════════════════
# D.1 Consistency score
# ════════════════════════════════════════════════════════════════════════════

# Rule 1 — advanced tooling with < 1.5 years of reported experience (−20)
CS_SENIOR_SKILLS = {
    'kubernetes', 'terraform', 'distributed systems', 'kafka', 'grpc',
    'microservices', 'system design',
}
CS_SENIOR_MIN_YEARS = 1.5
CS_SENIOR_PENALTY = 20
# Rule 2 — more skills than K_max = max(6, 4Y) (−12)
CS_SKILL_LIMIT_BASE, CS_SKILL_LIMIT_PER_YEAR = 6, 4
CS_SKILL_COUNT_PENALTY = 12
# Rule 3 — advanced skills without any foundational skill (−15)
CS_ADVANCED_SKILLS = {'kubernetes', 'terraform', 'kafka', 'pytorch', 'tensorflow'}
CS_FOUNDATIONAL_SKILLS = {'python', 'javascript', 'java', 'git', 'sql', 'linux'}
CS_FOUNDATION_PENALTY = 15


def compute_consistency(skills: Sequence[str], experience_years: Optional[float]) -> Dict:
    """
    CS_i = 100 − Σ_k d_ik over the three documented rules. Rules are
    independent and additive (all three can fire: minimum 53). No floor.
    Rules 1–2 need Y; when experience is unknown they are not evaluated.
    """
    s = {x.lower() for x in skills}
    flags, skipped = [], []
    score = 100

    if experience_years is None:
        skipped += ['senior_skills_low_experience', 'skill_count_vs_experience']
    else:
        senior = sorted(s & CS_SENIOR_SKILLS)
        if senior and experience_years < CS_SENIOR_MIN_YEARS:
            score -= CS_SENIOR_PENALTY
            flags.append({
                'rule': 'senior_skills_low_experience', 'deduction': CS_SENIOR_PENALTY,
                'message': f"Advanced skills ({', '.join(senior)}) with {experience_years:.1f} years "
                           f"of reported experience (< {CS_SENIOR_MIN_YEARS}).",
            })
        k_max = max(CS_SKILL_LIMIT_BASE, CS_SKILL_LIMIT_PER_YEAR * experience_years)
        if len(s) > k_max:
            score -= CS_SKILL_COUNT_PENALTY
            flags.append({
                'rule': 'skill_count_vs_experience', 'deduction': CS_SKILL_COUNT_PENALTY,
                'message': f"{len(s)} skills listed; expected at most {k_max:g} for "
                           f"{experience_years:.1f} years (K_max = max(6, 4Y)).",
            })

    advanced = sorted(s & CS_ADVANCED_SKILLS)
    if advanced and not (s & CS_FOUNDATIONAL_SKILLS):
        score -= CS_FOUNDATION_PENALTY
        flags.append({
            'rule': 'advanced_without_foundation', 'deduction': CS_FOUNDATION_PENALTY,
            'message': f"Advanced skills ({', '.join(advanced)}) without a foundational skill "
                       f"(python, javascript, java, git, sql, linux).",
        })

    return {'score': float(score), 'flags': flags, 'rules_skipped': skipped}


# ════════════════════════════════════════════════════════════════════════════
# D.2 Skill validation score
# ════════════════════════════════════════════════════════════════════════════

# The paper's verb list, with inflections ("build" → build/builds/building/built).
ACTION_VERB_FORMS = {
    'build': r'build(?:s|ing)?|built',
    'develop': r'develop(?:s|ed|ing)?',
    'design': r'design(?:s|ed|ing)?',
    'implement': r'implement(?:s|ed|ing)?',
    'deploy': r'deploy(?:s|ed|ing)?',
    'create': r'creat(?:e|es|ed|ing)',
    'architect': r'architect(?:s|ed|ing)?',
    'lead': r'lead(?:s|ing)?|led',
    'manage': r'manag(?:e|es|ed|ing)',
    'integrate': r'integrat(?:e|es|ed|ing)',
    'automate': r'automat(?:e|es|ed|ing)',
    'migrate': r'migrat(?:e|es|ed|ing)',
    'scale': r'scal(?:e|es|ed|ing)',
    'deliver': r'deliver(?:s|ed|ing)?',
    'maintain': r'maintain(?:s|ed|ing)?',
    'configure': r'configur(?:e|es|ed|ing)',
}
ACTION_VERB_RE = re.compile(r'\b(?:' + '|'.join(ACTION_VERB_FORMS.values()) + r')\b', re.IGNORECASE)


_SKILL_NAME_VERB_RE = None


def _skill_names_with_verbs() -> re.Pattern:
    """
    Skill names that contain a verb form ("responsive design", "system design",
    "design system"). Those words name a skill, they are not evidence of doing
    something, so they are masked before looking for action verbs.
    """
    global _SKILL_NAME_VERB_RE
    if _SKILL_NAME_VERB_RE is None:
        try:
            from .extraction import SKILL_CATALOG
            names = {a for aliases in SKILL_CATALOG.values() for a in aliases} | set(SKILL_CATALOG)
        except Exception:
            names = set()
        names |= {'design system', 'design systems', 'system design', 'responsive design', 'ui design',
                  'ux design', 'web design', 'database design'}
        names = sorted((n for n in names if ACTION_VERB_RE.search(n)), key=len, reverse=True)
        _SKILL_NAME_VERB_RE = re.compile('|'.join(re.escape(n) for n in names) or r'(?!x)x', re.IGNORECASE)
    return _SKILL_NAME_VERB_RE


_LIST_SEPARATOR_RE = re.compile(r'\s*(?:[•|·▪●,;]|\s-\s)\s*')


def is_list_line(line: str) -> bool:
    """A skills/tools list ("React • Redux • Jest", "Java, Spring, MySQL, Docker") —
    enumerations, not sentences about work done."""
    items = [x for x in _LIST_SEPARATOR_RE.split(line.strip(' •-*\t')) if x.strip()]
    if len(items) < 4:
        return False
    return sum(len(x.split()) for x in items) / len(items) <= 3


def _has_action_verb(window: str):
    return ACTION_VERB_RE.search(_skill_names_with_verbs().sub(' ', window))


def classify_skill_evidence(skill: str, spans: List[Tuple[int, int]], text: str,
                            mode: Optional[str] = None) -> Dict:
    """
    Valid       action verb within VS_WINDOW_CHARS of the first mention
                (mode='any': of any mention)
    Partial     no such verb, but the skill is mentioned ≥ 2 times
    Unverified  otherwise (including: not found in the text)
    """
    if not spans:
        return {'skill': skill, 'status': 'Unverified', 'mentions': 0, 'evidence': None}
    mode = (mode or VS_EVIDENCE_MODE)
    candidates = spans[:1] if mode == 'first' else spans
    window, verb = '', None
    for start, end in candidates:
        if mode == 'sentence':
            line_start = text.rfind('\n', 0, start) + 1
            line_end = text.find('\n', end)
            window = text[line_start:line_end if line_end != -1 else len(text)]
            if is_list_line(window):
                continue
        else:
            window = text[max(0, start - VS_WINDOW_CHARS):min(len(text), end + VS_WINDOW_CHARS)]
        verb = _has_action_verb(window)
        if verb:
            break
    if verb:
        status = 'Valid'
    elif len(spans) >= 2:
        status = 'Partial'
    else:
        status = 'Unverified'
    return {
        'skill': skill, 'status': status, 'mentions': len(spans),
        'evidence': re.sub(r'\s+', ' ', window).strip() if verb else None,
    }


def compute_skill_validation(classified: List[Dict]) -> Optional[float]:
    """VS_i = V_i / N_i × 100. None when N_i = 0 (undefined; not treated as 0)."""
    n = len(classified)
    if n == 0:
        return None
    v = sum(1 for c in classified if c['status'] == 'Valid')
    return round(v / n * 100.0, 2)


def compute_jd_evidence(validated_sentence: List[Dict], jd_skills: Iterable[str]) -> Optional[float]:
    """
    JD-conditioned evidence (VS_JD, extension — not in the paper's §IV.D.2):
    share of the skills the JOB DESCRIPTION asks for that the résumé backs with
    an action verb in the same sentence/bullet. Listing a skill without saying
    what was done with it earns nothing, so keyword stuffing does not help.
    None when the JD names no catalogue skills.
    """
    jd = {s.lower() for s in jd_skills}
    if not jd:
        return None
    valid = {v['skill'].lower() for v in validated_sentence if v.get('status') == 'Valid'}
    return round(len(jd & valid) / len(jd) * 100.0, 2)


def evidence_band(vs: Optional[float]) -> str:
    """Heuristic interpretation bands from the paper (> 70 / 40–70 / < 40)."""
    if vs is None:
        return 'Not available'
    if vs > 70:
        return 'Stronger evidence'
    if vs >= 40:
        return 'Mixed evidence'
    return 'Weaker evidence'


# ════════════════════════════════════════════════════════════════════════════
# D.3 Learning velocity
# ════════════════════════════════════════════════════════════════════════════

def _month_idx(label: str) -> Optional[int]:
    m = re.fullmatch(r'(\d{4})-(\d{2})', label or '')
    return int(m.group(1)) * 12 + int(m.group(2)) - 1 if m else None


def skill_timeline(text: str, positions: List[Dict], extract_skills_fn,
                   heading_fn=None) -> List[Dict]:
    """
    Attribute skills to dated positions: each position owns the lines from its
    date line up to the next position (or the next section heading).
    Returns positions in chronological order with their skills.
    """
    lines = (text or '').splitlines()
    with_lines = sorted((p for p in positions if isinstance(p.get('line'), int)), key=lambda p: p['line'])
    out = []
    for i, p in enumerate(with_lines):
        stop = with_lines[i + 1]['line'] if i + 1 < len(with_lines) else len(lines)
        block = []
        for j in range(p['line'], stop):
            if j > p['line'] and heading_fn and heading_fn(lines[j]):
                break
            block.append(lines[j])
        start, end = _month_idx(p.get('start')), _month_idx(p.get('end'))
        if start is None or end is None:
            continue
        out.append({'start': start, 'end': end, 'title': p.get('title', ''),
                    'skills': set(extract_skills_fn('\n'.join(block)))})
    out.sort(key=lambda p: (p['start'], p['end']))
    return out


def compute_learning_velocity_raw(timeline: List[Dict]) -> Dict:
    """
    LV_raw = N_new / Δt
      N_new  distinct skills first appearing in a position after the earliest one
      Δt     years from the start of the earliest to the end of the latest position
             (floored at LV_MIN_SPAN_YEARS)
    Requires ≥ 2 dated positions and ≥ 1 skill attributed to a position;
    otherwise None (a single résumé snapshot cannot show when skills were acquired).
    """
    if len(timeline) < 2 or not any(p['skills'] for p in timeline):
        return {'raw': None, 'new_skills': [], 'span_years': None,
                'basis': 'insufficient dated history'}
    baseline = set(timeline[0]['skills'])
    seen, new = set(baseline), []
    for p in timeline[1:]:
        for s in sorted(p['skills'] - seen):
            new.append(s)
        seen |= p['skills']
    span_months = max(p['end'] for p in timeline) + 1 - timeline[0]['start']
    span_years = max(LV_MIN_SPAN_YEARS, span_months / 12.0)
    return {'raw': round(len(new) / span_years, 4), 'new_skills': new,
            'span_years': round(span_years, 2),
            'basis': f'{len(timeline)} dated positions'}


def normalize_min_max(raw: Optional[float], raw_min: float, raw_max: float) -> Optional[float]:
    """
    LV = (raw − min) / (max − min), clipped to [0, 1].
    Equal min and max (e.g. a single candidate) → 0.5: LV then carries no
    ranking information and does not move candidates relative to each other.
    """
    if raw is None:
        return None
    if raw_max <= raw_min:
        return 0.5
    return round(min(1.0, max(0.0, (raw - raw_min) / (raw_max - raw_min))), 4)


def normalize_lv_batch(raw_values: Iterable[Optional[float]]) -> List[Optional[float]]:
    """Min–max over the candidate set being ranked (the paper's normalisation set)."""
    values = list(raw_values)
    present = [v for v in values if v is not None]
    if not present:
        return [None] * len(values)
    lo, hi = min(present), max(present)
    return [normalize_min_max(v, lo, hi) for v in values]


def lv_label(lv_score: Optional[float]) -> str:
    if lv_score is None:
        return 'N/A'
    if lv_score >= 66.67:
        return 'High'
    if lv_score >= 33.33:
        return 'Medium'
    return 'Low'


# ════════════════════════════════════════════════════════════════════════════
# E. Aggregation
# ════════════════════════════════════════════════════════════════════════════

def compute_analytical(cs: Optional[float], vs: Optional[float], lv_score: Optional[float]) -> Dict:
    """AS = (CS + VS + LV) / 3 over the available components (all on 0–100)."""
    parts = {'CS': cs, 'VS': vs, 'LV': lv_score}
    available = {k: v for k, v in parts.items() if v is not None}
    missing = [k for k, v in parts.items() if v is None]
    if not available:
        return {'score': None, 'components_used': [], 'missing': missing}
    return {'score': round(sum(available.values()) / len(available), 2),
            'components_used': list(available), 'missing': missing}


def compute_final(ss: Optional[float], as_score: Optional[float],
                  w_ss: Optional[float] = None, w_as: Optional[float] = None) -> Dict:
    """FS = w_ss·SS + w_as·AS (paper: 0.6 / 0.4). If one side is unavailable
    the other is used alone; if both are, FS is 0 and flagged by the caller."""
    w_ss = W_SS if w_ss is None else w_ss
    w_as = W_AS if w_as is None else w_as
    if ss is None and as_score is None:
        return {'score': 0.0, 'weights': {'SS': 0.0, 'AS': 0.0}}
    if as_score is None:
        return {'score': round(float(ss), 2), 'weights': {'SS': 1.0, 'AS': 0.0}}
    if ss is None:
        return {'score': round(float(as_score), 2), 'weights': {'SS': 0.0, 'AS': 1.0}}
    total = w_ss + w_as
    w_ss, w_as = w_ss / total, w_as / total
    return {'score': round(w_ss * ss + w_as * as_score, 2),
            'weights': {'SS': round(w_ss, 4), 'AS': round(w_as, 4)}}


def final_fit(fs: float) -> str:
    if fs >= FIT_HIGH:
        return 'High'
    if fs >= FIT_MEDIUM:
        return 'Medium'
    return 'Low'


def score_candidate(ss: Optional[float], cs: Optional[float], vs: Optional[float], lv_raw: Optional[float],
                    lv_min: float = LV_RAW_MIN_REF, lv_max: float = LV_RAW_MAX_REF,
                    w_ss: Optional[float] = None, w_as: Optional[float] = None,
                    lv_norm: Optional[float] = None) -> Dict:
    """
    One candidate's full score breakdown. Pass lv_norm when LV was normalised
    over a candidate set (ranking); otherwise the reference bounds are used.
    """
    if lv_norm is None:
        lv_norm = normalize_min_max(lv_raw, lv_min, lv_max)
    lv_score = None if lv_norm is None else round(lv_norm * 100.0, 2)
    analytical = compute_analytical(cs, vs, lv_score)
    final = compute_final(ss, analytical['score'], w_ss, w_as)
    return {
        'semantic_score': None if ss is None else round(float(ss), 2),
        'consistency_score': cs,
        'skill_validation_score': vs,
        'lv_raw': lv_raw,
        'lv_normalized': lv_norm,
        'lv_score': lv_score,
        'analytical_score': analytical['score'],
        'analytical_components': analytical['components_used'],
        'missing_components': (['SS'] if ss is None else []) + analytical['missing'],
        'final_score': final['score'],
        'weights': final['weights'],
        'final_fit': final_fit(final['score']),
    }
