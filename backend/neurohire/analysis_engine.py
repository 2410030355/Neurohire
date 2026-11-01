import fitz
import re
import os
import logging
import requests
import time
import json
from typing import Dict, List, Optional, Tuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import threading

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Semantic similarity is computed via the Gemini embedding API (see
# get_similarity_score below), not a locally loaded model — this removes
# PyTorch/Sentence-Transformers from the process entirely, which was the
# single largest memory consumer on constrained hosting (e.g. Render Free).
# TfidfVectorizer (below, in get_similarity_score) is the offline fallback
# if the Gemini embedding call fails for any reason.


# ==============================
# Information extraction (paper §IV.B) — see extraction.py
# ==============================
from .extraction import (
    SKILL_KEYWORDS,
    GEMINI_EMBEDDING_MODEL,
    extract_skills,
    extract_experience,
    extract_education,
    experience_from_positions,
    extract_with_gemini,
    find_skill_spans,
    merge_skills,
    redact_for_embedding,
    strip_annotation_lines,
    get_gemini_client as _get_gemini_client,
    _heading_kind,
)
from . import scoring
from .scoring import (
    classify_skill_evidence,
    compute_consistency,
    compute_learning_velocity_raw,
    compute_skill_validation,
    evidence_band,
    lv_label,
    score_candidate,
    similarity_to_score,
    skill_timeline,
)


# ==============================
# Recruiter-feedback weights (paper §IV.H) — see feedback.py
# ==============================
from . import feedback


def get_current_weights() -> Dict[str, float]:
    """Weights FS uses now (configured 0.6/0.4 unless ADAPTIVE_WEIGHTS=1)."""
    w = feedback.get_scoring_weights()
    return {'semantic_weight': w['w_ss'], 'analytical_weight': w['w_as'], 'source': w['source']}




# ==============================
# Sentence Transformer Utilities
# ==============================



# Embedding task type sent to Gemini. SEMANTIC_SIMILARITY matches how the
# vectors are used (cosine between résumé and JD). Set the env var to an empty
# string to send no task type.
GEMINI_EMBEDDING_TASK_TYPE = os.environ.get('GEMINI_EMBEDDING_TASK_TYPE', 'SEMANTIC_SIMILARITY').strip()


def _get_gemini_embeddings(texts: List[str]) -> Optional[List[np.ndarray]]:
    """
    Embed several texts in ONE Gemini API call (résumé + job description
    together: half the requests and latency of one call per text).
    Returns None on any failure — caller falls back to TF-IDF. Never raises.
    """
    client = _get_gemini_client()
    if client is None or not texts:
        return None
    try:
        kwargs = {'model': GEMINI_EMBEDDING_MODEL, 'contents': list(texts)}
        if GEMINI_EMBEDDING_TASK_TYPE:
            kwargs['config'] = {'task_type': GEMINI_EMBEDDING_TASK_TYPE}
        response = client.models.embed_content(**kwargs)
        embeddings = getattr(response, 'embeddings', None)
        if not embeddings or len(embeddings) != len(texts):
            return None
        vectors = []
        for emb in embeddings:
            values = getattr(emb, 'values', None)
            if not values:
                return None
            vectors.append(np.asarray(values, dtype=float))
        return vectors
    except Exception as e:
        logger.error(f"Gemini embedding request failed: {e}")
        return None


def _get_gemini_embedding(text: str) -> Optional[np.ndarray]:
    """Single-text wrapper, kept for existing callers."""
    vectors = _get_gemini_embeddings([text])
    return vectors[0] if vectors else None


def _tfidf_cosine(resume_text: str, job_description_text: str) -> Optional[float]:
    """
    Offline fallback (paper §IV.C.1): TF-IDF vectors + cosine. A lexical
    representation, not a semantic embedding. None if it cannot be computed.
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform([resume_text, job_description_text])
        return float(cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])[0][0])
    except Exception as e:
        logger.error(f"TF-IDF fallback similarity failed: {e}")
        return None


def _tfidf_similarity(resume_text: str, job_description_text: str) -> float:
    """TF-IDF cosine × 100 (kept for existing callers)."""
    cos = _tfidf_cosine(resume_text, job_description_text)
    return 0.0 if cos is None else float(cos * 100)


def get_similarity_details(resume_text: str, job_description_text: str) -> Dict:
    """
    SS_i = cosine(e_r, e_j) (paper eq. C.2), reported x100 and clipped to 0-100.

    Representation: Gemini embeddings (gemini-embedding-001) in one batched
    call; TF-IDF cosine if Gemini is unavailable. Returns
    {'score': float|None, 'cosine': float|None, 'method': 'gemini'|'tfidf'|'none'}.
    """
    if not resume_text or not resume_text.strip() or not job_description_text or not job_description_text.strip():
        return {'score': None, 'cosine': None, 'method': 'none'}

    resume_text = resume_text.strip()[:6000]
    job_description_text = job_description_text.strip()[:6000]

    vectors = _get_gemini_embeddings([resume_text, job_description_text])
    if vectors is not None:
        try:
            cos = float(cosine_similarity([vectors[0]], [vectors[1]])[0][0])
            return {'score': similarity_to_score(cos), 'cosine': round(cos, 6), 'method': 'gemini',
                    'resume_embedding': [float(x) for x in vectors[0]]}
        except Exception as e:
            logger.error(f"Error computing Gemini embedding similarity: {e}")

    logger.info("Gemini embeddings unavailable — using TF-IDF fallback for similarity score.")
    cos = _tfidf_cosine(resume_text, job_description_text)
    if cos is None:
        return {'score': None, 'cosine': None, 'method': 'none'}
    return {'score': similarity_to_score(cos), 'cosine': round(cos, 6), 'method': 'tfidf'}


EMBED_BATCH_SIZE = 50        # texts per Gemini embed_content call
SIMILARITY_TEXT_CAP = 6000   # characters per text sent for similarity


def embedding_cache_key(text: str) -> str:
    """Cache key: changes when the text, model or task type changes."""
    import hashlib
    payload = f"{GEMINI_EMBEDDING_MODEL}|{GEMINI_EMBEDDING_TASK_TYPE}|{(text or '').strip()[:SIMILARITY_TEXT_CAP]}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def get_similarity_batch(resume_texts: List[str], job_description_text: str,
                         caches: Optional[List[Optional[dict]]] = None) -> Dict:
    """
    SS for many résumés against one JD (ranking). One representation for the
    whole set — if any Gemini call fails, every candidate falls back to TF-IDF
    so scores stay comparable.

    caches: optional per-résumé {'key': ..., 'values': [...]} from MongoDB;
    reused when the key matches, so stored candidates are embedded only once.
    Returns {'scores', 'cosines', 'method', 'new_embeddings'} where
    new_embeddings[i] is a cache dict to store (or None if nothing new).
    """
    n = len(resume_texts)
    caches = caches or [None] * n
    jd = (job_description_text or '').strip()[:SIMILARITY_TEXT_CAP]
    texts = [(t or '').strip()[:SIMILARITY_TEXT_CAP] for t in resume_texts]
    empty = {'scores': [None] * n, 'cosines': [None] * n, 'method': 'none', 'new_embeddings': [None] * n}
    if not jd or n == 0:
        return empty

    keys = [embedding_cache_key(t) for t in texts]
    vectors: List[Optional[np.ndarray]] = [None] * n
    for i, c in enumerate(caches):
        if c and c.get('key') == keys[i] and c.get('values'):
            vectors[i] = np.asarray(c['values'], dtype=float)

    todo = [i for i in range(n) if vectors[i] is None and texts[i]]
    jd_vec, ok = None, _get_gemini_client() is not None
    if ok:
        batch_texts = [jd] + [texts[i] for i in todo]
        got: List[np.ndarray] = []
        for start in range(0, len(batch_texts), EMBED_BATCH_SIZE):
            chunk = _get_gemini_embeddings(batch_texts[start:start + EMBED_BATCH_SIZE])
            if chunk is None:
                ok = False
                break
            got.extend(chunk)
        if ok:
            jd_vec = got[0]
            for i, vec in zip(todo, got[1:]):
                vectors[i] = vec

    if ok and jd_vec is not None:
        scores, cosines, new = [], [], []
        for i in range(n):
            if vectors[i] is None:
                scores.append(None); cosines.append(None); new.append(None)
                continue
            cos = float(cosine_similarity([vectors[i]], [jd_vec])[0][0])
            scores.append(similarity_to_score(cos)); cosines.append(round(cos, 6))
            new.append({'key': keys[i], 'values': [float(x) for x in vectors[i]]} if i in todo else None)
        return {'scores': scores, 'cosines': cosines, 'method': 'gemini', 'new_embeddings': new}

    logger.info("Gemini embeddings unavailable for ranking — TF-IDF fallback for every candidate.")
    scores, cosines = [], []
    for t in texts:
        cos = _tfidf_cosine(t, jd) if t else None
        cosines.append(None if cos is None else round(cos, 6))
        scores.append(None if cos is None else similarity_to_score(cos))
    return {'scores': scores, 'cosines': cosines, 'method': 'tfidf', 'new_embeddings': [None] * n}


def get_similarity_score(resume_text: str, job_description_text: str) -> float:
    """SS on 0-100 (0 if it cannot be computed). Kept for existing callers."""
    score = get_similarity_details(resume_text, job_description_text)['score']
    return 0.0 if score is None else score


# Email and phone regex patterns
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_PATTERN = re.compile(r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}')

# ==============================
# Text Extraction
# ==============================

def extract_text_from_pdf(file_path: str) -> Tuple[str, str]:
    """
    Extract text from PDF or DOCX file.
    Returns: (lowercase_text, original_case_text)
    Raises: Exception if file cannot be read
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path.lower())[1]

    # ── DOCX handling ──────────────────────────────────────────────
    if ext in ('.docx', '.doc'):
        try:
            import docx as python_docx
            doc = python_docx.Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            # Also extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            paragraphs.append(cell.text)
            text = "\n".join(paragraphs)
            if not text.strip():
                raise ValueError("DOCX contains no extractable text")
            return text.lower(), text
        except ImportError:
            raise ValueError("python-docx not installed. Run: pip install python-docx")
        except Exception as e:
            logger.error(f"Failed to extract text from DOCX: {str(e)}")
            raise

    # ── PDF handling ───────────────────────────────────────────────
    if ext == '.pdf':
        try:
            import fitz as pymupdf
            text = ""
            doc = pymupdf.open(file_path)
            for page in doc:
                text += page.get_text()
            doc.close()
            if not text.strip():
                raise ValueError("PDF contains no extractable text (may be scanned image)")
            return text.lower(), text
        except ImportError:
            raise ValueError("PyMuPDF not installed. Run: pip install PyMuPDF")
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {str(e)}")
            raise

    raise ValueError(f"Unsupported file type: {ext}. Please upload PDF or DOCX.")


# ==============================
# Core Extractors
# ==============================

def extract_email(text: str) -> Optional[str]:
    """Extract email address from resume."""
    emails = EMAIL_PATTERN.findall(text)
    # Return first valid email found
    return emails[0] if emails else None


def extract_phone(text: str) -> Optional[str]:
    """Extract phone number from resume."""
    phones = PHONE_PATTERN.findall(text)
    # Return first phone that looks valid (at least 10 digits)
    for phone in phones:
        digits = re.sub(r'\D', '', phone)
        if len(digits) >= 10:
            return phone
    return None


def extract_name(text: str) -> Optional[str]:
    """
    Improved name extraction using multiple strategies.
    Looks at first few lines and validates against common patterns.
    """
    lines = text.split("\n")

    # Common resume headers to skip
    skip_keywords = [
        'resume', 'cv', 'curriculum vitae', 'profile', 'objective',
        'contact', 'email', 'phone', 'address', 'linkedin'
    ]

    for line in lines[:15]:  # Check first 15 lines
        clean = line.strip()
        clean_lower = clean.lower()

        # Skip empty lines and headers
        if not clean or any(skip in clean_lower for skip in skip_keywords):
            continue

        # Check if line looks like a name
        words = clean.split()
        if 2 <= len(words) <= 4:  # Names are usually 2-4 words
            # No digits, reasonable length, mostly alphabetic
            if (not any(char.isdigit() for char in clean) and
                    len(clean) < 40 and
                    sum(c.isalpha() or c.isspace() for c in clean) / len(clean) > 0.8):
                return clean.title()

    return None


# ==============================
# Intelligence Scores
# ==============================

# Paper-exact scoring lives in scoring.py; these wrappers keep the old names.

def compute_role_match(resume_text: str, target_role: str, skills: List[str] = None,
                       job_description: str = "") -> Optional[float]:
    """
    Semantic similarity SS (paper §IV.C): cosine between the (redacted) résumé
    and the job description — or the target role when no JD is given — x100.
    No keyword bonus is added. None when there is nothing to match against.
    """
    target = job_description.strip() if job_description and job_description.strip() else (target_role or '')
    return get_similarity_details(resume_text, target)['score']


def compute_consistency_score(skills: List[str], experience_years: Optional[float]) -> float:
    """CS (paper §IV.D.1). See scoring.compute_consistency for flags."""
    return compute_consistency(skills, experience_years)['score']


def validate_skills_from_text(skills: List[str], text: str) -> List[dict]:
    """Valid / Partial / Unverified per skill (paper §IV.D.2)."""
    return [classify_skill_evidence(skill, find_skill_spans(text, skill), text) for skill in skills]


def compute_skill_validation_score(validated_skills: List[dict]) -> Optional[float]:
    """VS = V / N x 100; None when no skills were recognised."""
    return compute_skill_validation(validated_skills)


def compute_learning_velocity(text: str, positions: List[Dict]) -> Dict:
    """LV_raw = N_new / Δt from dated positions (paper §IV.D.3)."""
    timeline = skill_timeline(text, positions, extract_skills, heading_fn=_heading_kind)
    return compute_learning_velocity_raw(timeline)


def compute_resume_strength_score(skills: List[str], education: Optional[str],
                                  experience_years: float) -> float:
    """Overall resume strength based on completeness and quality."""
    base_score = 30
    skill_bonus = min(35, len(skills) * 3)

    education_bonus = 0
    if education:
        education_levels = {
            "PhD": 20,
            "Master's Degree": 15,
            "MBA": 15,
            "Bachelor's Degree": 12,
            "Associate Degree": 8,
            "Diploma": 5
        }
        education_bonus = education_levels.get(education, 5)

    experience_bonus = min(15, experience_years * 2)

    total = base_score + skill_bonus + education_bonus + experience_bonus
    return round(min(100, total), 2)


def compute_analytical_score(consistency_score: Optional[float],
                             skill_validation_score: Optional[float],
                             lv_score: Optional[float]) -> Optional[float]:
    """AS = (CS + VS + LV) / 3 over available components (paper §IV.E.1)."""
    return scoring.compute_analytical(consistency_score, skill_validation_score, lv_score)['score']


def compute_final_score(semantic_score: Optional[float], analytical_score: Optional[float],
                        alpha: float = None, beta: float = None) -> float:
    """FS = w_SS*SS + w_AS*AS (paper §IV.E.2): 0.6/0.4 unless ADAPTIVE_WEIGHTS=1."""
    if alpha is None or beta is None:
        w = feedback.get_scoring_weights()
        alpha, beta = w['w_ss'], w['w_as']
    return scoring.compute_final(semantic_score, analytical_score, alpha, beta)['score']


def compute_final_fit(final_score: float) -> str:
    """High >= 70, Medium >= 40, Low < 40."""
    return scoring.final_fit(final_score)


def generate_career_trajectory(skills: List[str], learning_velocity: str,
                               experience_years: Optional[float]) -> str:
    """Generate a meaningful career trajectory summary."""
    skill_count = len(skills)

    if skill_count >= 15:
        skill_level = "extensive"
    elif skill_count >= 8:
        skill_level = "strong"
    else:
        skill_level = "developing"

    if experience_years is not None:
        exp = f"{experience_years:.1f} years of experience"
    else:
        exp = "experience not stated with dates"
    if learning_velocity == 'N/A':
        lv = "learning velocity not measurable (needs dated positions)"
    else:
        lv = f"{learning_velocity.lower()} learning velocity"
    return (
        f"Candidate demonstrates {skill_level} technical expertise with "
        f"{skill_count} identified skills, {lv}, and {exp}."
    )


# ==============================
# ✅ MAIN ANALYSIS FUNCTION
# ==============================

def _fmt(v, suffix=''):
    return 'n/a' if v is None else f"{v:.0f}{suffix}"


def _build_explanation(scores, similarity, consistency, validated_skills, lv, has_jd,
                       experience_years, experience_source) -> str:
    """Component-level account of how FS was computed (not a validity claim)."""
    counts = {k: sum(1 for v in validated_skills if v['status'] == k) for k in ('Valid', 'Partial', 'Unverified')}
    method = {'gemini': 'Gemini embeddings', 'tfidf': 'TF-IDF fallback', 'none': 'not computed'}[similarity['method']]
    target = 'the job description' if has_jd else 'the target role'
    if consistency['flags']:
        cs_detail = " - " + "; ".join(f['message'] for f in consistency['flags'])
    else:
        cs_detail = " - no rule triggered"
    if consistency['rules_skipped']:
        cs_detail += " (experience-based rules skipped: no dated or stated experience)"
    if lv['raw'] is not None:
        lv_text = (f"Learning velocity (LV): {_fmt(scores['lv_score'])}/100 - {len(lv['new_skills'])} new skills "
                   f"over {lv['span_years']} years ({lv['basis']}).")
    else:
        lv_text = "Learning velocity (LV): not available - needs at least two dated positions that mention skills."
    parts = [
        f"Semantic similarity (SS) to {target}: {_fmt(scores['semantic_score'])}/100 ({method}).",
        f"Consistency (CS): {_fmt(scores['consistency_score'])}/100{cs_detail}.",
        f"Skill validation (VS): {_fmt(scores['skill_validation_score'])}/100 - "
        f"{counts['Valid']} valid, {counts['Partial']} partial, {counts['Unverified']} unverified.",
        lv_text,
        f"Analytical score (AS) = mean of {', '.join(scores['analytical_components']) or 'no components'}: "
        f"{_fmt(scores['analytical_score'])}/100.",
        f"Final score (FS) = {scores['weights']['SS']:g}*SS + {scores['weights']['AS']:g}*AS = "
        f"{scores['final_score']:.0f}/100 ({scores['final_fit']} fit).",
    ]
    if experience_years is not None:
        parts.append(f"Experience: {experience_years:.1f} years ({experience_source}).")
    return ' '.join(parts)


def analyze_resume(file_path: str, target_role: str = "", job_description: str = "") -> Dict:
    """
    Main function to analyze a resume PDF/DOCX and extract comprehensive insights.

    Extraction strategy: try Gemini structured extraction first (name, email,
    skills, experience_years, education). If it fails for any reason — no API
    key, SDK error, timeout, malformed JSON — silently fall back to the
    original regex-based extractors. Phone and all scoring always run
    against the locally extracted text regardless of which path was used,
    since Gemini's schema doesn't include phone and the scoring functions
    need the raw text either way.

    Args:
        file_path: Path to the resume file (PDF or DOCX)
        target_role: Target job role for matching (optional)
        job_description: Full job description text for richer matching (optional)

    Returns:
        Dict containing all analysis results

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is not a PDF/DOCX or contains no text
        Exception: For other processing errors
    """
    try:
        # Extract text (both lowercase and original case) — always needed,
        # regardless of extraction path, for scoring and phone lookup.
        text_lower, text_original = extract_text_from_pdf(file_path)
        # Drop annotation lines (e.g. the evaluation files' "Ground Truth Label")
        # so they can never influence extraction or similarity.
        text_original = strip_annotation_lines(text_original)
        text_lower = text_original.lower()

        # ── Structured extraction (paper §IV.B) ─────────────────────────
        # Deterministic regex/date parsing is the primary source for skills and
        # experience (reproducible scores). Gemini, when configured, adds
        # employment/projects structure and fills gaps; its skills are only
        # kept if they are actually written in the résumé.
        gemini_result = extract_with_gemini(text_original)
        extraction_method = 'gemini+regex' if gemini_result else 'regex'
        g = gemini_result or {}

        name = g.get('name') or extract_name(text_original)
        email = g.get('email') or extract_email(text_original)
        phone = extract_phone(text_original)

        skills, other_skills = merge_skills(
            text_original, extract_skills(text_original), g.get('skills', []))

        experience = extract_experience(text_original)
        employment_history = experience['positions']
        experience_source = experience['source']
        if experience['dated_years'] is None and g.get('employment'):
            gemini_years = experience_from_positions(g['employment'])
            if gemini_years:
                experience['dated_years'] = gemini_years
                experience_source = 'dated (gemini)'
            employment_history = g['employment']
        claimed_years = experience['claimed_years'] or g.get('claimed_experience_years')
        experience_years = experience['dated_years'] or claimed_years or 0.0
        if not experience['dated_years']:
            experience_source = 'claimed' if claimed_years else 'none'

        education = extract_education(text_original)
        if not education and g.get('education'):
            education = extract_education(' '.join(str(e.get('degree') or '') for e in g['education'])) \
                or (g['education'][0].get('degree') or None)
        projects = g.get('projects', [])

        # Text used for semantic similarity: name, contact details and
        # personal attributes removed so they cannot influence the score.
        redacted_text = redact_for_embedding(text_original, name=name)
        experience_known = experience_source != 'none'
        years_for_rules = float(experience_years) if experience_known else None

        # ── SS: semantic similarity (paper §IV.C) ───────────────────────
        has_jd = bool(job_description and job_description.strip())
        match_target = job_description.strip() if has_jd else (target_role or '').strip()
        similarity = get_similarity_details(redacted_text, match_target)
        ss = similarity['score']

        # ── CS: consistency (paper §IV.D.1) ─────────────────────────────
        consistency = compute_consistency(skills, years_for_rules)

        # ── VS: skill validation (paper §IV.D.2) ────────────────────────
        validated_skills = validate_skills_from_text(skills, text_original)
        vs = compute_skill_validation(validated_skills)

        # ── LV: learning velocity (paper §IV.D.3) ───────────────────────
        lv = compute_learning_velocity(text_original, experience['positions'])

        # ── AS and FS (paper §IV.E) ─────────────────────────────────────
        weights = feedback.get_scoring_weights()
        scores = score_candidate(ss, consistency['score'], vs, lv['raw'],
                                 w_ss=weights['w_ss'], w_as=weights['w_as'])
        learning_velocity = lv_label(scores['lv_score'])

        resume_strength_score = compute_resume_strength_score(skills, education, experience_years)
        career_trajectory = generate_career_trajectory(
            skills, learning_velocity, experience_years if experience_known else None)

        # Skills the JD asks for that the résumé does not mention
        jd_skills = extract_skills(job_description) if has_jd else []
        missing_skills = [s for s in jd_skills if s not in skills]

        explainability = _build_explanation(scores, similarity, consistency, validated_skills, lv,
                                            has_jd, experience_years if experience_known else None,
                                            experience_source)

        profile_summary = (
            f"{name or 'Candidate'} - {education or 'Education not specified'} | "
            f"{len(skills)} skills | "
            + (f"{experience_years:.1f} years experience" if experience_known else "experience not dated")
        )

        logger.info(f"Successfully analyzed resume: {name or 'Unknown'} (extraction: {extraction_method})")

        return {
            # Basic Information
            "name": name,
            "email": email,
            "phone": phone,

            # Skills
            "skills": skills,
            "other_skills": other_skills,
            "missing_skills": missing_skills,
            "jd_skills": jd_skills,

            # Experience and Education
            "experience_years": experience_years if experience_known else None,
            "experience_years_dated": experience['dated_years'],
            "experience_years_claimed": claimed_years,
            "experience_source": experience_source,
            "employment_history": employment_history,
            "projects": projects,
            "education": education,

            # SS (paper §IV.C). role_match_score kept: it is the field the UI reads.
            "semantic_score": scores['semantic_score'],
            "role_match_score": scores['semantic_score'],
            "similarity_method": similarity['method'],
            "similarity_cosine": similarity['cosine'],

            # Analytical components (paper §IV.D)
            "consistency_score": consistency['score'],
            "consistency_flags": consistency['flags'],
            "consistency_rules_skipped": consistency['rules_skipped'],
            "skill_validation_score": vs,
            "skill_evidence_band": evidence_band(vs),
            "validated_skills": validated_skills,
            "lv_raw": lv['raw'],
            "lv_normalized": scores['lv_normalized'],
            "lv_score": scores['lv_score'],
            "lv_new_skills": lv['new_skills'],
            "lv_span_years": lv['span_years'],
            "lv_basis": lv['basis'],
            "learning_velocity": learning_velocity,

            # Aggregation (paper §IV.E): AS = mean(CS, VS, LV); FS = 0.6*SS + 0.4*AS
            "analytical_score": scores['analytical_score'],
            "analytical_components": scores['analytical_components'],
            "missing_components": scores['missing_components'],
            "final_score": scores['final_score'],
            "score_weights": scores['weights'],
            "final_fit": scores['final_fit'],

            # Supplementary (not part of FS)
            "resume_strength_score": resume_strength_score,

            # Insights
            "career_trajectory": career_trajectory,
            "profile_summary": profile_summary,
            "explainability": explainability,

            "extraction_method": extraction_method,

            # For re-ranking against other job descriptions (stored, never shown)
            "resume_text_redacted": redacted_text,
            "embedding_cache": ({'key': embedding_cache_key(redacted_text),
                                 'values': similarity['resume_embedding']}
                                if similarity.get('resume_embedding') else None),
        }

    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except ValueError as e:
        logger.error(f"Invalid file or content: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during resume analysis: {str(e)}")
        raise Exception(f"Resume analysis failed: {str(e)}")


# ==============================
# GitHub Candidate Search Service
# ==============================

GITHUB_API_BASE = "https://api.github.com"
GITHUB_SEARCH_USERS = f"{GITHUB_API_BASE}/search/users"
GITHUB_USER_REPOS = f"{GITHUB_API_BASE}/users/{{username}}/repos"
GITHUB_USER_PROFILE = f"{GITHUB_API_BASE}/users/{{username}}"

GITHUB_REQUEST_TIMEOUT = 10
GITHUB_RATE_LIMIT_DELAY = 1
MAX_REPOS_TO_ANALYZE = 30


def _make_github_request(url: str, params: Optional[Dict] = None,
                         timeout: int = GITHUB_REQUEST_TIMEOUT) -> Optional[Dict]:
    try:
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'NeuroHire-Recruiter-Platform'
        }

        github_token = os.environ.get('GITHUB_TOKEN')
        if github_token:
            headers['Authorization'] = f'token {github_token}'

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=timeout
        )

        if response.status_code == 403:
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', '0')
            if rate_limit_remaining == '0':
                reset_time = response.headers.get('X-RateLimit-Reset', 'unknown')
                logger.warning(f"GitHub API rate limit exceeded. Resets at: {reset_time}")
                return None

        response.raise_for_status()
        time.sleep(GITHUB_RATE_LIMIT_DELAY)
        return response.json()

    except requests.exceptions.Timeout:
        logger.error(f"GitHub API request timeout for URL: {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"GitHub API request failed: {str(e)}")
        return None
    except ValueError as e:
        logger.error(f"Failed to parse GitHub API response: {str(e)}")
        return None


def _extract_languages_from_repos(username: str, max_repos: int = MAX_REPOS_TO_ANALYZE) -> Dict[str, int]:
    languages_aggregate = {}

    try:
        repos_url = GITHUB_USER_REPOS.format(username=username)
        params = {
            'sort': 'updated',
            'direction': 'desc',
            'per_page': max_repos
        }

        repos_data = _make_github_request(repos_url, params)
        if not repos_data:
            return languages_aggregate

        for repo in repos_data[:max_repos]:
            if repo.get('fork', False):
                continue

            language = repo.get('language')
            if language:
                languages_aggregate[language] = languages_aggregate.get(language, 0) + 1

        return languages_aggregate

    except Exception as e:
        logger.error(f"Failed to extract languages for user {username}: {str(e)}")
        return languages_aggregate


def _get_top_languages(languages_dict: Dict[str, int], top_n: int = 5) -> List[str]:
    if not languages_dict:
        return []

    sorted_languages = sorted(
        languages_dict.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return [lang for lang, _ in sorted_languages[:top_n]]


def _format_github_user(user_data: Dict, languages: List[str]) -> Dict:
    return {
        'username': user_data.get('login', ''),
        'profile_url': user_data.get('html_url', ''),
        'avatar_url': user_data.get('avatar_url', ''),
        'bio': user_data.get('bio', '') or 'No bio available',
        'name': user_data.get('name', '') or user_data.get('login', ''),
        'location': user_data.get('location', ''),
        'email': user_data.get('email', ''),
        'company': user_data.get('company', ''),
        'public_repos': user_data.get('public_repos', 0),
        'followers': user_data.get('followers', 0),
        'following': user_data.get('following', 0),
        'created_at': user_data.get('created_at', ''),
        'top_languages': languages,
        'profile_score': _calculate_github_profile_score(user_data, languages),
    }


def _calculate_github_profile_score(user_data: Dict, languages: List[str]) -> float:
    score = 0.0

    repos = user_data.get('public_repos', 0)
    score += min(30, repos * 1.5)

    followers = user_data.get('followers', 0)
    score += min(25, followers * 0.5)

    score += min(20, len(languages) * 4)

    if user_data.get('bio'):
        score += 10

    if user_data.get('company'):
        score += 8

    if user_data.get('location'):
        score += 7

    return round(min(100, score), 2)


def github_search_service(query: str, max_results: int = 10) -> Dict:
    try:
        if not query or not query.strip():
            return {
                'success': False,
                'error': 'Search query is required',
                'data': [],
                'total_count': 0,
                'query': query
            }

        max_results = min(max_results, 100)

        logger.info(f"GitHub search initiated: query='{query}', max_results={max_results}")

        search_params = {
            'q': query,
            'per_page': max_results,
            'sort': 'followers',
            'order': 'desc'
        }

        search_response = _make_github_request(GITHUB_SEARCH_USERS, search_params)

        if not search_response:
            return {
                'success': False,
                'error': 'GitHub API request failed or rate limit exceeded',
                'data': [],
                'total_count': 0,
                'query': query
            }

        total_count = search_response.get('total_count', 0)
        users = search_response.get('items', [])

        logger.info(f"Found {total_count} users, processing {len(users)} results")

        formatted_users = []
        for user in users:
            username = user.get('login')
            if not username:
                continue

            profile_url = GITHUB_USER_PROFILE.format(username=username)
            user_details = _make_github_request(profile_url)

            if not user_details:
                user_details = user

            languages_dict = _extract_languages_from_repos(username)
            top_languages = _get_top_languages(languages_dict)

            formatted_user = _format_github_user(user_details, top_languages)
            formatted_users.append(formatted_user)

            logger.info(f"Processed user: {username} ({len(top_languages)} languages)")

        logger.info(f"GitHub search completed successfully: {len(formatted_users)} users processed")

        return {
            'success': True,
            'data': formatted_users,
            'total_count': total_count,
            'query': query,
            'results_returned': len(formatted_users)
        }

    except Exception as e:
        logger.error(f"GitHub search service failed: {str(e)}")
        return {
            'success': False,
            'error': f'Search failed: {str(e)}',
            'data': [],
            'total_count': 0,
            'query': query
        }