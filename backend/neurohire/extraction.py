"""
extraction.py — résumé information extraction for NeuroHire (paper §IV.B).

Everything here turns raw résumé text into structured fields:

  * extract_skills()         catalog-based skill detection (symbol-safe: c++, c#,
                             .net, node.js; ambiguous names like Go / R / C only
                             counted with supporting context)
  * find_skill_spans()       where a skill is mentioned (used by skill validation)
  * extract_experience()     employment periods parsed from date ranges
                             (overlaps merged, education/projects ignored) plus
                             the "N years of experience" the résumé claims
  * extract_education()      highest degree, without "Scrum Master" /
                             "Associate Engineer" false positives
  * redact_for_embedding()   removes name, contact details and personal
                             attributes before text is embedded
  * extract_with_gemini()    optional LLM extraction (structured JSON, timeout,
                             model names from env vars)

The regex/date path is deterministic and is the primary source for skills and
experience, so scores are reproducible. Gemini adds fields the regex path can't
get (employment history structure, projects) and acts as a fallback.
"""
import json
import logging
import os
import re
import threading
from bisect import bisect_right
from datetime import date
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════
# 1. Skills
# ════════════════════════════════════════════════════════════════════════════
#
# canonical name -> aliases (all matched case-insensitively with symbol-safe
# boundaries). Canonical names are what the rest of the app stores and shows.

SKILL_CATALOG: Dict[str, List[str]] = {
    # ── Languages ──
    "python": ["python", "python3"], "java": ["java"],
    "javascript": ["javascript", "js", "es6", "es2015", "ecmascript"], "typescript": ["typescript", "ts"],
    "c++": ["c++", "cpp"], "c#": ["c#", "csharp"], "php": ["php"], "ruby": ["ruby"], "golang": ["golang"],
    "rust": ["rust"], "kotlin": ["kotlin"], "scala": ["scala"], "matlab": ["matlab"], "dart": ["dart"],
    "sql": ["sql"], "bash": ["bash", "shell scripting"], "powershell": ["powershell"],
    "solidity": ["solidity"],
    # ── Frontend ──
    "react": ["react", "react.js", "reactjs", "react js"], "next.js": ["next.js", "nextjs", "next js"],
    "angular": ["angular", "angularjs"], "vue": ["vue", "vue.js", "vuejs"],
    "nuxt": ["nuxt", "nuxt.js", "nuxtjs"], "svelte": ["svelte", "sveltekit"],
    "redux": ["redux", "redux toolkit", "rtk query"], "zustand": ["zustand"], "mobx": ["mobx"],
    "rxjs": ["rxjs"], "html": ["html", "html5"], "css": ["css", "css3"], "sass": ["sass", "scss"],
    "tailwind": ["tailwind", "tailwindcss", "tailwind css"], "bootstrap": ["bootstrap"],
    "material ui": ["material ui", "material-ui", "mui"],
    "styled-components": ["styled-components", "styled components"], "jquery": ["jquery"],
    "webpack": ["webpack"], "vite": ["vite"], "babel": ["babel"], "jest": ["jest"], "vitest": ["vitest"],
    "react testing library": ["react testing library", "testing library"], "cypress": ["cypress"],
    "playwright": ["playwright"], "storybook": ["storybook"], "graphql": ["graphql"],
    "apollo": ["apollo", "apollo client"], "websockets": ["websocket", "websockets", "socket.io"],
    "pwa": ["pwa", "progressive web app", "progressive web apps"],
    "ssr": ["ssr", "server-side rendering", "server side rendering"],
    "web performance": ["web performance", "core web vitals", "web vitals", "lighthouse"],
    "accessibility": ["accessibility", "a11y", "wcag", "aria"],
    "responsive design": ["responsive design", "responsive web design"],
    "micro-frontends": ["micro-frontends", "micro frontends", "microfrontends", "module federation"],
    "figma": ["figma"], "d3.js": ["d3", "d3.js"], "three.js": ["three.js", "threejs"], "eslint": ["eslint"],
    # ── Backend ──
    "node.js": ["node.js", "nodejs", "node js"], "express": ["express.js", "expressjs"],
    "nestjs": ["nestjs", "nest.js"], "django": ["django", "django rest framework", "drf"],
    "flask": ["flask"], "fastapi": ["fastapi"],
    "spring boot": ["spring boot", "springboot", "spring framework"], "asp.net": ["asp.net", "asp.net core"],
    ".net": [".net", "dotnet", ".net core"], "laravel": ["laravel"], "rails": ["ruby on rails", "rails"],
    "rest api": ["rest api", "rest apis", "restful", "restful api", "restful apis", "rest"],
    "grpc": ["grpc"], "microservices": ["microservices", "microservice", "micro-services"],
    "system design": ["system design"], "distributed systems": ["distributed systems", "distributed system"],
    "kafka": ["kafka", "apache kafka"], "rabbitmq": ["rabbitmq"], "celery": ["celery"],
    # ── Databases ──
    "postgresql": ["postgresql", "postgres"], "mysql": ["mysql"],
    "mongodb": ["mongodb", "mongo", "mongoose"], "redis": ["redis"],
    "elasticsearch": ["elasticsearch", "elastic search"], "sqlite": ["sqlite"],
    "oracle": ["oracle db", "oracle database", "pl/sql"], "sql server": ["sql server", "mssql"],
    "dynamodb": ["dynamodb"], "cassandra": ["cassandra"], "firebase": ["firebase", "firestore"],
    "supabase": ["supabase"], "prisma": ["prisma"],
    # ── Cloud & DevOps ──
    "aws": ["aws", "amazon web services", "ec2", "s3", "aws lambda"], "azure": ["azure", "microsoft azure"],
    "gcp": ["gcp", "google cloud", "google cloud platform"],
    "docker": ["docker", "dockerfile", "docker-compose", "docker compose"],
    "kubernetes": ["kubernetes", "k8s", "helm"], "terraform": ["terraform"], "ansible": ["ansible"],
    "jenkins": ["jenkins"], "github actions": ["github actions"], "gitlab ci": ["gitlab ci", "gitlab-ci"],
    "ci/cd": ["ci/cd", "ci cd", "cicd", "continuous integration"], "nginx": ["nginx"],
    "linux": ["linux", "ubuntu", "unix"], "git": ["git", "github", "gitlab", "bitbucket"],
    "prometheus": ["prometheus"], "grafana": ["grafana"], "vercel": ["vercel"],
    # ── Data & ML ──
    "machine learning": ["machine learning", "ml"], "deep learning": ["deep learning"],
    "nlp": ["nlp", "natural language processing"], "computer vision": ["computer vision", "opencv"],
    "tensorflow": ["tensorflow"], "pytorch": ["pytorch"], "keras": ["keras"],
    "scikit-learn": ["scikit-learn", "sklearn", "scikit learn"], "pandas": ["pandas"], "numpy": ["numpy"],
    "data analysis": ["data analysis", "data analytics"], "data science": ["data science"],
    "spark": ["apache spark", "pyspark", "spark"], "tableau": ["tableau"],
    "power bi": ["power bi", "powerbi"], "llm": ["llm", "llms", "large language models", "langchain", "rag"],
    # ── Mobile ──
    "android": ["android"], "ios": ["ios"], "react native": ["react native"], "flutter": ["flutter"],
    "swiftui": ["swiftui"],
    # ── Practices & tools ──
    "agile": ["agile"], "scrum": ["scrum"], "jira": ["jira"],
    "tdd": ["tdd", "test-driven development", "test driven development"],
    "unit testing": ["unit testing", "unit tests"], "pytest": ["pytest"], "junit": ["junit"],
    "selenium": ["selenium"], "blockchain": ["blockchain"],
    # ── Added for the multi-role benchmark (fixed before any benchmark run) ──
    # Testing / QA
    "manual testing": ["manual testing"], "automation testing": ["automation testing", "test automation"],
    "test cases": ["test cases", "test case design", "test scenarios"], "test planning": ["test plan", "test planning"],
    "regression testing": ["regression testing"], "functional testing": ["functional testing"],
    "integration testing": ["integration testing"], "system testing": ["system testing"],
    "api testing": ["api testing"], "performance testing": ["performance testing", "load testing"],
    "uat": ["uat", "user acceptance testing"], "defect tracking": ["defect tracking", "bug tracking", "defect management"],
    "sdlc": ["sdlc"], "stlc": ["stlc"], "testng": ["testng"], "appium": ["appium"], "jmeter": ["jmeter"],
    "postman": ["postman"], "cucumber": ["cucumber", "bdd"], "qtp": ["qtp", "uft"], "loadrunner": ["loadrunner"],
    "bugzilla": ["bugzilla"],
    # Java ecosystem
    "hibernate": ["hibernate"], "j2ee": ["j2ee", "java ee", "jee"], "jsp": ["jsp"], "servlets": ["servlets", "servlet"],
    "jdbc": ["jdbc"], "struts": ["struts"], "maven": ["maven"], "gradle": ["gradle"],
    # Data science
    "matplotlib": ["matplotlib"], "seaborn": ["seaborn"], "scipy": ["scipy"], "xgboost": ["xgboost"],
    "statistics": ["statistics", "statistical analysis"], "hadoop": ["hadoop"], "hive": ["hive", "apache hive"],
    "excel": ["excel", "ms excel"],
    # DevOps
    "puppet": ["puppet"], "nagios": ["nagios"], "sonarqube": ["sonarqube"],
    "openshift": ["openshift"], "cloudformation": ["cloudformation"], "splunk": ["splunk"],
    "elk": ["elk stack", "elk", "logstash", "kibana"],
    # Web design
    "photoshop": ["photoshop"], "illustrator": ["illustrator"], "wordpress": ["wordpress"],
    "dreamweaver": ["dreamweaver"],
}

# Ambiguous names: only counted when the line looks like a skills list (≥2 other
# skills on it) or one of the explicit context patterns matches.
AMBIGUOUS_SKILLS: Dict[str, Dict] = {
    # Case-sensitive "Go" (not "go to market"); context patterns are case-insensitive.
    "golang": {"token": r"Go", "context": [r"\bgo\s*(?:lang|programming|language|developer|routines?)\b",
                                            r"\bgoroutines?\b"]},
    "r": {"token": r"R", "context": [r"\br\s*(?:programming|language|studio)\b", r"\brstudio\b",
                                      r"\btidyverse\b", r"\bggplot2?\b", r"\bshiny\b"]},
    "c": {"token": r"C", "context": [r"\bc\s*/\s*c\+\+", r"\bc\s*programming\b", r"\bansi\s*c\b",
                                      r"\bembedded\s*c\b", r"\bc\s*language\b"]},
    "express": {"token": r"[Ee]xpress", "context": [r"\bexpress(?:\.js|js)\b"]},
    "spring boot": {"token": r"Spring", "context": [r"\bspring\s*(?:boot|framework|mvc)\b"]},
    "swift": {"token": r"Swift", "context": [r"\bswiftui\b", r"\bswift\s*(?:programming|language)\b"]},
    "less": {"token": r"LESS|Less", "context": [r"\bless\s*css\b"]},
    "ruby": {"token": r"Ruby", "context": [r"\bruby\s*on\s*rails\b"]},
    "artificial intelligence": {"token": r"AI", "context": [r"\bartificial\s+intelligence\b"]},
}

# Ambiguous canonical names must not also be matched freely through the catalog.
_CATALOG_SKIP_FREE = {"ruby"}

# Characters that make up a skill token (so "c++" does not match inside "c++17x"
# and "java" does not match inside "javascript").
_TOKEN_CHARS = r"A-Za-z0-9+#"


def _alias_regex(alias: str) -> str:
    return rf"(?<![{_TOKEN_CHARS}.]){re.escape(alias)}(?![{_TOKEN_CHARS}])"


_ALIAS_PATTERNS: Dict[str, re.Pattern] = {
    canonical: re.compile("|".join(_alias_regex(a) for a in sorted(aliases, key=len, reverse=True)),
                          re.IGNORECASE)
    for canonical, aliases in SKILL_CATALOG.items()
    if canonical not in _CATALOG_SKIP_FREE
}

# Short aliases that are also common English / abbreviations: require context too.
_WEAK_ALIASES = {"js", "ts", "rest", "ml", "rag", "aria", "mui", "drf", "s3", "ec2", "helm",
                 "mongo", "unix", "spark", "apollo", "babel", "jest", "vite", "rails",
                 # common words that are only skills next to other skills
                 "hive", "excel", "elk", "puppet", "cucumber", "statistics", "uat", "jee", "illustrator"}

# Canonical skill names, for code that needs a flat list (e.g. "missing skills").
SKILL_KEYWORDS: List[str] = list(SKILL_CATALOG.keys())


def _skill_lines(text: str) -> List[str]:
    return [ln for ln in text.splitlines() if ln.strip()]


def _strong_matches_on_line(line: str) -> set:
    found = set()
    for canonical, pattern in _ALIAS_PATTERNS.items():
        for m in pattern.finditer(line):
            if m.group(0).lower() not in _WEAK_ALIASES:
                found.add(canonical)
                break
    return found


def _extract_skills_reference(text: str) -> List[str]:
    """Original line-by-line implementation, kept to verify the fast version (tests)."""
    if not text:
        return []
    found = set()
    lines = _skill_lines(text)
    line_strong = [_strong_matches_on_line(ln) for ln in lines]

    # Catalog skills. Weak aliases ("js", "rest", "ml", "jest"…) count only when
    # another strong skill is named on the same line ("tested React UI with Jest").
    for idx, line in enumerate(lines):
        for canonical, pattern in _ALIAS_PATTERNS.items():
            for m in pattern.finditer(line):
                if m.group(0).lower() not in _WEAK_ALIASES or (line_strong[idx] - {canonical}):
                    found.add(canonical)
                    break

    # Ambiguous names (Go, R, C, Express, Spring, Swift, LESS, Ruby, AI)
    for canonical, rule in AMBIGUOUS_SKILLS.items():
        if canonical in found:
            continue
        if any(re.search(p, text, re.IGNORECASE) for p in rule["context"]):
            found.add(canonical)
            continue
        token_re = re.compile(rf"(?<![{_TOKEN_CHARS}.]){rule['token']}(?![{_TOKEN_CHARS}])")
        for idx, line in enumerate(lines):
            if token_re.search(line) and len(line_strong[idx] - {canonical}) >= 2:
                found.add(canonical)
                break
    return sorted(found)



def _line_index(text: str):
    """(starts, ids): start offset of every splitlines() line and its index among
    non-empty lines (None for blank lines) — maps a match position to its line."""
    starts, ids, pos, n = [], [], 0, 0
    for raw in text.splitlines(keepends=True):
        starts.append(pos)
        if raw.strip():
            ids.append(n)
            n += 1
        else:
            ids.append(None)
        pos += len(raw)
    return starts, ids


def extract_skills(text: str) -> List[str]:
    """Sorted canonical skills in the text (a new list each call; see _extract_skills_cached)."""
    return list(_extract_skills_cached(text or ''))


@lru_cache(maxsize=8192)
def _extract_skills_cached(text: str) -> Tuple[str, ...]:
    """
    Return sorted canonical skills found in résumé text (original case preferred).

    Same result as the line-by-line definition (_extract_skills_reference):
    weak aliases count only when another strong skill is on the same line;
    ambiguous names need a context pattern or a skills-list line. Each alias
    pattern scans the whole text once and matches are mapped back to lines,
    which is much faster on long résumés. Results are cached per text.
    """
    if not text:
        return ()
    starts, ids = _line_index(text)
    lines = _skill_lines(text)
    line_strong = [set() for _ in lines]
    hits = []                                      # (canonical, line, is_weak)
    for canonical, pattern in _ALIAS_PATTERNS.items():
        for m in pattern.finditer(text):
            li = ids[bisect_right(starts, m.start()) - 1]
            if li is None:
                continue
            weak = m.group(0).lower() in _WEAK_ALIASES
            hits.append((canonical, li, weak))
            if not weak:
                line_strong[li].add(canonical)

    found = set()
    for canonical, li, weak in hits:
        if canonical not in found and (not weak or (line_strong[li] - {canonical})):
            found.add(canonical)

    # Ambiguous names (Go, R, C, Express, Spring, Swift, LESS, Ruby, AI)
    for canonical, rule in AMBIGUOUS_SKILLS.items():
        if canonical in found:
            continue
        if any(re.search(p, text, re.IGNORECASE) for p in rule["context"]):
            found.add(canonical)
            continue
        token_re = _ambiguous_token_re(rule['token'])
        for idx, line in enumerate(lines):
            if len(line_strong[idx] - {canonical}) >= 2 and token_re.search(line):
                found.add(canonical)
                break
    return tuple(sorted(found))


@lru_cache(maxsize=64)
def _ambiguous_token_re(token: str) -> re.Pattern:
    return re.compile(rf"(?<![{_TOKEN_CHARS}.]){token}(?![{_TOKEN_CHARS}])")


def find_skill_spans(text: str, skill: str) -> List[Tuple[int, int]]:
    """(start, end) of every mention of a canonical skill (any alias) in text."""
    if not text or not skill:
        return []
    skill = skill.lower()
    patterns = []
    if skill in _ALIAS_PATTERNS:
        patterns.append(_ALIAS_PATTERNS[skill])
    if skill in AMBIGUOUS_SKILLS:
        rule = AMBIGUOUS_SKILLS[skill]
        patterns.append(re.compile(rf"(?<![{_TOKEN_CHARS}.]){rule['token']}(?![{_TOKEN_CHARS}])"))
        patterns.extend(re.compile(p, re.IGNORECASE) for p in rule["context"])
    if not patterns:  # unknown skill: plain symbol-safe match
        patterns.append(re.compile(_alias_regex(skill), re.IGNORECASE))
    spans = {(m.start(), m.end()) for p in patterns for m in p.finditer(text)}
    return sorted(spans)


def normalize_skill(name: str) -> Optional[str]:
    """Map a free-text skill (e.g. from Gemini: 'React.js') to its canonical name."""
    if not name:
        return None
    n = name.strip().lower()
    if n in SKILL_CATALOG or n in AMBIGUOUS_SKILLS:
        return n
    for canonical, aliases in SKILL_CATALOG.items():
        if n in aliases:
            return canonical
    if n in ("go", "go lang"):
        return "golang"
    return None


# ════════════════════════════════════════════════════════════════════════════
# 2. Experience (date ranges)
# ════════════════════════════════════════════════════════════════════════════

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTH_RE = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
             r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?")
_DATE_RE = (
    rf"(?:{_MONTH_RE}[\s,'’\-]*(?:(?:19|20)\d{{2}}|['’]\d{{2}})"   # Jan 2020, Jan '20
    r"|(?:0?[1-9]|1[0-2])\s*[/\-.]\s*(?:19|20)\d{2}"              # 01/2020, 1-2020
    r"|(?:19|20)\d{2}\s*[/\-]\s*(?:0[1-9]|1[0-2])(?!\d)"          # 2020-01
    r"|(?:19|20)\d{2})"                                            # 2020
)
_PRESENT_RE = r"(?:present|current(?:ly)?|now|till\s+date|to\s+date|ongoing|today)"
_RANGE_RE = re.compile(
    rf"(?P<start>{_DATE_RE})\s*(?:-|–|—|~|to|till|until|through)\s*(?P<end>{_DATE_RE}|{_PRESENT_RE})\b",
    re.IGNORECASE,
)

_HEADING_KINDS = [
    ("work", r"(?:work|professional|relevant|industry)?\s*experience|employment(?:\s+history)?|"
             r"work\s+history|career(?:\s+history)?|internships?(?:\s+experience)?|experience\s*&\s*internships?"),
    ("education", r"education(?:al)?(?:\s+(?:background|qualifications?|details))?|academics?|"
                  r"academic\s+(?:background|qualifications?|details)|qualifications?"),
    ("projects", r"(?:academic|personal|key|major|technical|selected)?\s*projects?"),
    ("other", r"(?:technical\s+)?skills(?:\s*&\s*\w+)?|certifications?|certificates|achievements|awards|"
              r"summary|profile|objective|career\s+objective|publications|languages|interests|hobbies|"
              r"extra[\s-]?curricular(?:\s+activities)?|activities|contact|declaration|references|"
              r"positions?\s+of\s+responsibility|volunteering|leadership|courses|coursework"),
]
_HEADING_RES = [(kind, re.compile(rf"^\s*(?:{rx})\s*:?\s*$", re.IGNORECASE)) for kind, rx in _HEADING_KINDS]

_EDU_LINE_RE = re.compile(
    r"\b(?:university|college|school|institute|institution|academy|b\.?\s?tech|m\.?\s?tech|bachelor|"
    r"master'?s?\s+of|b\.?\s?e\b|b\.?\s?sc|m\.?\s?sc|bca|mca|mba|ph\.?\s?d|cgpa|gpa|"
    r"percentage|degree|diploma|intermediate|ssc|hsc|cbse|icse|class\s+(?:x|xii|10|12))\b",
    re.IGNORECASE,
)

_CLAIMED_RE = [
    re.compile(r"(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years?|yrs?)\.?\s*(?:of\s+)?(?:[a-z\-]+\s+){0,3}?experience",
               re.IGNORECASE),
    re.compile(r"experience\s*(?:of|:|-)\s*(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years?|yrs?)", re.IGNORECASE),
]


def _heading_kind(line: str) -> Optional[str]:
    s = re.sub(r"^[^A-Za-z]+|[^A-Za-z)]+$", "", line.strip())
    if not s or len(s) > 45:
        return None
    for kind, rx in _HEADING_RES:
        if rx.match(s):
            return kind
    return None


def parse_date(token: str, is_end: bool = False, today: Optional[date] = None) -> Optional[Tuple[int, bool]]:
    """Parse a résumé date into (month_index, month_precise). month_index = year*12 + (month-1).

    'Present' → current month. Year-only dates use mid-year so "2019 – 2021" = 2 years.
    """
    today = today or date.today()
    t = (token or "").strip().lower().replace("’", "'")
    if not t:
        return None
    if re.fullmatch(_PRESENT_RE, t, re.IGNORECASE):
        return today.year * 12 + today.month - 1, True
    m = re.match(rf"({_MONTH_RE})[\s,'\-]*((?:19|20)\d{{2}}|'\d{{2}})", t, re.IGNORECASE)
    if m:
        mon = _MONTHS[m.group(1).rstrip(".")[:3]]
        yr = m.group(2)
        year = 2000 + int(yr[1:]) if yr.startswith("'") else int(yr)
        return year * 12 + mon - 1, True
    m = re.fullmatch(r"(0?[1-9]|1[0-2])\s*[/\-.]\s*((?:19|20)\d{2})", t)
    if m:
        return int(m.group(2)) * 12 + int(m.group(1)) - 1, True
    m = re.fullmatch(r"((?:19|20)\d{2})\s*[/\-]\s*(0[1-9]|1[0-2])", t)
    if m:
        return int(m.group(1)) * 12 + int(m.group(2)) - 1, True
    m = re.fullmatch(r"((?:19|20)\d{2})", t)
    if m:
        return int(m.group(1)) * 12 + 6, False
    return None


def _interval(start_tok, end_tok, today) -> Optional[Tuple[int, int]]:
    """Half-open month interval [start, end) or None if unusable."""
    s = parse_date(start_tok, today=today)
    e = parse_date(end_tok, is_end=True, today=today)
    if not s or not e:
        return None
    start, s_precise = s
    end, e_precise = e
    # Month-precise ranges are inclusive of the end month ("Jan–Dec 2020" = 12 months)
    if s_precise and e_precise:
        end += 1
    now_idx = today.year * 12 + today.month
    end = min(end, now_idx)
    if end <= start or end - start > 50 * 12:
        return None
    return start, end


def merge_months(intervals: List[Tuple[int, int]]) -> int:
    """Total months covered by intervals, counting overlaps once."""
    total, cur_s, cur_e = 0, None, None
    for s, e in sorted(intervals):
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += cur_e - cur_s
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += cur_e - cur_s
    return total


def _month_label(idx: int) -> str:
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def extract_claimed_years(text: str) -> Optional[float]:
    """Largest 'N years of experience' statement in the résumé, or None."""
    values = []
    for rx in _CLAIMED_RE:
        for m in rx.finditer(text or ""):
            v = float(m.group(1))
            if 0 < v <= 50:
                values.append(v)
    return max(values) if values else None


def extract_experience(text: str, today: Optional[date] = None) -> Dict:
    """
    Work experience from date ranges in the résumé.

    Returns:
      positions      [{title, start, end, months, section, line}] in résumé order
      dated_years    total of merged (non-overlapping) work periods, or None
      claimed_years  largest "N years of experience" statement, or None
      years          dated_years if available, else claimed_years, else None
      source         'dated' | 'claimed' | 'none'

    Only ranges in a work/experience/internship section are counted. When the
    résumé has no recognisable work heading, ranges on education-looking lines
    and in the projects section are skipped instead.
    """
    today = today or date.today()
    lines = (text or "").splitlines()
    section = None
    has_work_heading = any(_heading_kind(ln) == "work" for ln in lines)
    positions, intervals = [], []
    prev_text = ""

    for line_no, line in enumerate(lines):
        kind = _heading_kind(line)
        if kind:
            section = kind
            continue
        for m in _RANGE_RE.finditer(line):
            if has_work_heading:
                if section != "work":
                    continue
            elif section in ("education", "projects") or _EDU_LINE_RE.search(line):
                continue
            iv = _interval(m.group("start"), m.group("end"), today)
            if not iv:
                continue
            label = (line[:m.start()] + " " + line[m.end():])
            label = re.sub(r"[\s|•·,–—\-()]+", " ", label).strip() or prev_text
            positions.append({
                "title": label[:120],
                "start": _month_label(iv[0]),
                "end": _month_label(iv[1] - 1),
                "months": iv[1] - iv[0],
                "section": section or "unlabelled",
                "line": line_no,
            })
            intervals.append(iv)
        if line.strip():
            prev_text = line.strip()

    dated = round(merge_months(intervals) / 12, 1) if intervals else None
    claimed = extract_claimed_years(text)
    if dated:
        years, source = dated, "dated"
    elif claimed:
        years, source = claimed, "claimed"
    else:
        years, source = None, "none"
    return {
        "positions": positions,
        "dated_years": dated,
        "claimed_years": claimed,
        "years": years,
        "source": source,
    }


def experience_from_positions(positions: List[Dict], today: Optional[date] = None) -> Optional[float]:
    """Merged years from structured positions (e.g. Gemini output with start/end strings)."""
    today = today or date.today()
    intervals = []
    for p in positions or []:
        if not p.get("start") or not p.get("end"):
            continue  # unknown dates: don't guess
        iv = _interval(str(p["start"]), str(p["end"]), today)
        if iv:
            intervals.append(iv)
    return round(merge_months(intervals) / 12, 1) if intervals else None


# ════════════════════════════════════════════════════════════════════════════
# 3. Education
# ════════════════════════════════════════════════════════════════════════════

_EDUCATION_LEVELS = [
    # (label, priority, pattern)
    ("PhD", 4, r"\bph\.?\s?d\b|\bdoctorate\b|\bdoctor\s+of\s+philosophy\b"),
    ("Master's Degree", 3, r"\bmaster'?s?\s+(?:of|in|degree)\b|\bm\.?\s?tech\b|\bm\.\s?e\.?\b|\bm\.?\s?sc\b|"
                           r"\bm\.\s?s\.?\b|\bms\s+in\b|\bmca\b|\bpost[\s-]?graduat"),
    ("MBA", 3, r"\bmba\b|\bmaster\s+of\s+business\b"),
    ("Bachelor's Degree", 2, r"\bbachelor'?s?\b|\bb\.?\s?tech\b|\bb\.\s?e\.?\b|\bb\.?\s?sc\b|\bb\.\s?s\.?\b|"
                             r"\bbca\b|\bb\.?\s?com\b|\bundergraduate\s+degree\b"),
    ("Associate Degree", 1, r"\bassociate\s+(?:degree|of\s+(?:arts|science|applied))\b"),
    ("Diploma", 1, r"\bdiploma\b"),
]


def extract_education(text: str) -> Optional[str]:
    """Highest degree mentioned (case-insensitive, word-bounded)."""
    best, best_p = None, 0
    for label, priority, rx in _EDUCATION_LEVELS:
        if priority > best_p and re.search(rx, text or "", re.IGNORECASE):
            best, best_p = label, priority
    return best


# Evaluation/annotation lines that must never reach scoring. The 12 evaluation
# résumés contain their own "Ground Truth Label: …" line; left in, it leaks the
# answer into the similarity score.
_ANNOTATION_LINE_RE = re.compile(
    r"^[ \t]*(?:ground[\s_-]*truth(?:[\s_-]*label)?|relevance[\s_-]*label|gt[\s_-]*label)\b.*$\n?",
    re.IGNORECASE | re.MULTILINE,
)


def strip_annotation_lines(text: str) -> str:
    return _ANNOTATION_LINE_RE.sub("", text or "")


# ════════════════════════════════════════════════════════════════════════════
# 4. Redaction (before embedding)
# ════════════════════════════════════════════════════════════════════════════

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
URL_RE = re.compile(r"(?:https?://|www\.)\S+|\b(?:linkedin\.com|github\.com|gitlab\.com|behance\.net|"
                    r"dribbble\.com|leetcode\.com|medium\.com)/\S*", re.IGNORECASE)
PHONE_CANDIDATE_RE = re.compile(r"(?:\+?\d[\d \t().-]{8,}\d)")
# "Field: value" lines with personal / protected attributes (common in Indian résumés)
_PERSONAL_FIELD_RE = re.compile(
    r"^[\s•\-*]*(?:date\s+of\s+birth|d\.?\s?o\.?\s?b\.?|birth\s*date|age|gender|sex|marital\s+status|"
    r"nationality|religion|caste|category|father'?s\s+name|mother'?s\s+name|husband'?s\s+name|"
    r"passport(?:\s+no\.?)?|aadhaa?r(?:\s+no\.?)?|pan(?:\s+no\.?)?|(?:permanent\s+|current\s+)?address|"
    r"languages\s+known)\s*[:\-–].*$",
    re.IGNORECASE | re.MULTILINE,
)
_BLIND_PRONOUN_RE = re.compile(r"\b(?:he|she|him|her|his|hers|himself|herself|male|female|married|unmarried)\b",
                               re.IGNORECASE)
_BLIND_HONORIFIC_RE = re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Mx|MR|MRS|MS)\b\.?")


def _is_phone(s: str) -> bool:
    digits = re.sub(r"\D", "", s)
    return 10 <= len(digits) <= 15


def redact_for_embedding(text: str, name: Optional[str] = None, blind: Optional[bool] = None) -> str:
    """
    Remove information that identifies the candidate or reveals protected
    attributes before the text is embedded / compared with a job description.

    Always removed: emails, phone numbers, URLs/profile links, the candidate's
    name, and personal-detail lines (DOB, gender, marital status, nationality,
    religion, parents' names, address, ID numbers).
    blind=True (or env REDACTION_BLIND=1) also removes gendered pronouns,
    honorifics and marital words.
    """
    if not text:
        return ""
    if blind is None:
        blind = os.environ.get("REDACTION_BLIND", "0") == "1"
    out = _PERSONAL_FIELD_RE.sub(" ", text)
    out = EMAIL_RE.sub(" ", out)
    out = URL_RE.sub(" ", out)
    out = PHONE_CANDIDATE_RE.sub(lambda m: " " if _is_phone(m.group(0)) else m.group(0), out)
    if name and name.strip():
        out = re.sub(re.escape(name.strip()), " ", out, flags=re.IGNORECASE)
        for part in name.split():
            # Name parts are removed as written (Title / UPPER case) unless they are
            # also a skill word, so a surname like "Swift" cannot wipe out a skill.
            if len(part) >= 3 and not normalize_skill(part) and part.lower() not in AMBIGUOUS_SKILLS:
                for form in {part.title(), part.upper(), part}:
                    out = re.sub(rf"\b{re.escape(form)}\b", " ", out)
    if blind:
        out = _BLIND_PRONOUN_RE.sub(" ", out)
        out = _BLIND_HONORIFIC_RE.sub(" ", out)
    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r"\n\s*\n+", "\n", out)
    return out.strip()


# ════════════════════════════════════════════════════════════════════════════
# 5. Gemini structured extraction
# ════════════════════════════════════════════════════════════════════════════

def _env(name: str, default: str) -> str:
    return (os.environ.get(name) or default).strip()


GEMINI_MODEL_PRIMARY = _env("GEMINI_MODEL_PRIMARY", "gemini-3.6-flash")
GEMINI_MODEL_FALLBACK = _env("GEMINI_MODEL_FALLBACK", "gemini-3.5-flash")
GEMINI_EMBEDDING_MODEL = _env("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
GEMINI_TIMEOUT_SECONDS = float(_env("GEMINI_TIMEOUT_SECONDS", "15"))
# GEMINI_EXTRACTION=0 turns LLM extraction off (fully deterministic runs for evaluation)
GEMINI_EXTRACTION_ENABLED = _env("GEMINI_EXTRACTION", "1") != "0"

_gemini_client = None
_gemini_lock = threading.Lock()


def get_gemini_client():
    """Shared Gemini client with the request timeout applied. None if unavailable. Never raises."""
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client
    with _gemini_lock:
        if _gemini_client is not None:
            return _gemini_client
        try:
            from django.conf import settings
            api_key = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY")
        except Exception:
            api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not configured — using regex extraction and TF-IDF similarity.")
            return None
        try:
            from google.genai import Client
            _gemini_client = Client(
                api_key=api_key,
                http_options={"timeout": int(GEMINI_TIMEOUT_SECONDS * 1000)},  # SDK expects milliseconds
            )
            return _gemini_client
        except Exception as e:
            logger.error(f"Failed to initialise Gemini client: {e}")
            return None


_STR = {"type": "string"}
GEMINI_RESUME_SCHEMA = {
    "type": "object",
    "properties": {
        "name": _STR,
        "email": _STR,
        "skills": {"type": "array", "items": _STR},
        "education": {"type": "array", "items": {"type": "object", "properties": {
            "degree": _STR, "institution": _STR, "start": _STR, "end": _STR}}},
        "employment": {"type": "array", "items": {"type": "object", "properties": {
            "title": _STR, "company": _STR, "start": _STR, "end": _STR,
            "skills_used": {"type": "array", "items": _STR}}}},
        "projects": {"type": "array", "items": {"type": "object", "properties": {
            "name": _STR, "technologies": {"type": "array", "items": _STR}, "start": _STR, "end": _STR}}},
        "claimed_experience_years": {"type": "number"},
    },
    "required": ["skills", "employment", "education", "projects"],
}

GEMINI_EXTRACTION_PROMPT = (
    "Extract the following résumé into JSON matching the given schema.\n"
    "Rules: copy facts only from the text, never infer or invent. Dates as written "
    "(e.g. 'Jan 2021', '2019', 'Present'); use an empty string when absent and 0 for "
    "claimed_experience_years when the résumé states no total. 'employment' is paid "
    "work and internships only (not education or projects). 'skills' are technologies "
    "and tools explicitly named in the text.\n\nRésumé text:\n{text}"
)


def _clean_json(raw: str) -> str:
    cleaned = (raw or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _as_list(v) -> list:
    if isinstance(v, list):
        return v
    return [v] if v else []


def _normalise_gemini(parsed: Dict) -> Dict:
    def objs(key, fields):
        out = []
        for item in _as_list(parsed.get(key)):
            if isinstance(item, dict):
                out.append({f: (item.get(f) if item.get(f) not in ("", []) else None) for f in fields})
            elif isinstance(item, str):
                out.append({fields[0]: item, **{f: None for f in fields[1:]}})
        return out

    claimed = parsed.get("claimed_experience_years", parsed.get("experience_years"))
    try:
        claimed = float(claimed) if claimed not in (None, "") else None
    except (TypeError, ValueError):
        claimed = None
    if claimed is not None and not (0 < claimed <= 50):
        claimed = None
    return {
        "name": (parsed.get("name") or None),
        "email": (parsed.get("email") or None),
        "skills": [str(s) for s in _as_list(parsed.get("skills")) if s],
        "education": objs("education", ["degree", "institution", "start", "end"]),
        "employment": objs("employment", ["title", "company", "start", "end", "skills_used"]),
        "projects": objs("projects", ["name", "technologies", "start", "end"]),
        "claimed_experience_years": claimed,
    }


def extract_with_gemini(text_original: str) -> Optional[Dict]:
    """Structured extraction via Gemini. None on any failure (caller falls back). Never raises."""
    if not GEMINI_EXTRACTION_ENABLED or not text_original or not text_original.strip():
        return None
    client = get_gemini_client()
    if client is None:
        return None
    prompt = GEMINI_EXTRACTION_PROMPT.format(text=text_original.strip()[:8000])
    with_schema = {"response_mime_type": "application/json", "response_json_schema": GEMINI_RESUME_SCHEMA,
                   "temperature": 0}
    json_only = {"response_mime_type": "application/json", "temperature": 0}
    attempts = [(m, cfg) for m in dict.fromkeys((GEMINI_MODEL_PRIMARY, GEMINI_MODEL_FALLBACK))
                for cfg in (with_schema, json_only)]
    for model_name, config in attempts:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt, config=config)
            raw = getattr(response, "text", None)
            if not raw:
                logger.warning(f"Gemini ({model_name}) returned an empty response.")
                continue
            result = _normalise_gemini(json.loads(_clean_json(raw)))
            logger.info(f"Gemini extraction succeeded using {model_name}.")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Gemini ({model_name}) returned invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Gemini extraction failed on {model_name}: {e}")
            if "timeout" in str(e).lower() or "timed out" in str(e).lower() or "deadline" in str(e).lower():
                break  # don't stack more timeouts onto the upload request
    return None


# ════════════════════════════════════════════════════════════════════════════
# 6. Combined profile extraction
# ════════════════════════════════════════════════════════════════════════════

def merge_skills(text: str, regex_skills: List[str], gemini_skills: List[str]) -> Tuple[List[str], List[str]]:
    """
    Final skill list = catalog skills found by regex, plus Gemini skills that map
    to a catalog skill AND are actually mentioned in the text (so the LLM cannot
    add skills the résumé never states). Gemini skills outside the catalog are
    returned separately as 'other_skills' (shown, not scored).
    """
    skills = set(regex_skills)
    other = []
    for raw in gemini_skills or []:
        canonical = normalize_skill(raw)
        if canonical in AMBIGUOUS_SKILLS:
            continue  # Go / R / C … only via the context rules in extract_skills
        if canonical:
            if canonical not in skills and find_skill_spans(text, canonical):
                skills.add(canonical)
        else:
            cleaned = str(raw).strip()
            if cleaned and cleaned.lower() not in {o.lower() for o in other} and \
                    re.search(re.escape(cleaned), text, re.IGNORECASE):
                other.append(cleaned)
    return sorted(skills), other[:30]
