import fitz
import re
import os
import logging
import requests
import time
from typing import Dict, List, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================
# Skill Database (Expanded)
# ==============================

SKILL_KEYWORDS = [
    # Programming Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "php", "ruby",
    "go", "golang", "rust", "swift", "kotlin", "scala", "r", "matlab",

    # Web Technologies
    "react", "angular", "vue", "vue.js", "node.js", "express", "django",
    "flask", "fastapi", "spring", "spring boot", "asp.net", "laravel",
    "html", "css", "sass", "less", "bootstrap", "tailwind", "jquery",

    # Databases
    "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
    "cassandra", "dynamodb", "oracle", "sql server", "sqlite", "mariadb",

    # Cloud & DevOps
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
    "jenkins", "gitlab", "github actions", "terraform", "ansible", "ci/cd",

    # Data Science & ML
    "machine learning", "deep learning", "neural networks", "tensorflow",
    "pytorch", "keras", "scikit-learn", "pandas", "numpy", "data analysis",
    "data science", "nlp", "computer vision", "ai", "artificial intelligence",

    # Mobile Development
    "android", "ios", "react native", "flutter", "xamarin", "mobile development",

    # Other Technologies
    "git", "linux", "bash", "powershell", "rest api", "graphql", "microservices",
    "agile", "scrum", "jira", "testing", "unit testing", "selenium", "pytest",
    "api", "backend", "frontend", "full stack", "devops", "blockchain", "solidity"
]

LEARNING_WORDS = [
    "learned", "built", "developed", "improved", "optimized",
    "created", "designed", "implemented", "architected", "led",
    "managed", "delivered", "achieved", "spearheaded", "initiated",
    "enhanced", "streamlined", "automated", "deployed", "scaled"
]

# Email and phone regex patterns
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_PATTERN = re.compile(r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}')

# Education keywords with levels
EDUCATION_KEYWORDS = {
    "phd": "PhD",
    "doctorate": "PhD",
    "ph.d": "PhD",
    "master": "Master's Degree",
    "m.tech": "Master's Degree",
    "m.s": "Master's Degree",
    "msc": "Master's Degree",
    "mba": "MBA",
    "bachelor": "Bachelor's Degree",
    "b.tech": "Bachelor's Degree",
    "b.e": "Bachelor's Degree",
    "b.s": "Bachelor's Degree",
    "bsc": "Bachelor's Degree",
    "associate": "Associate Degree",
    "diploma": "Diploma"
}


# ==============================
# Text Extraction
# ==============================

def extract_text_from_pdf(file_path: str) -> Tuple[str, str]:
    """
    Extract text from PDF file.
    Returns: (lowercase_text, original_case_text)
    Raises: Exception if PDF cannot be read
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if not file_path.lower().endswith('.pdf'):
        raise ValueError("Only PDF files are supported")

    try:
        text = ""
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
        doc.close()

        if not text.strip():
            raise ValueError("PDF contains no extractable text")

        return text.lower(), text
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {str(e)}")
        raise


# ==============================
# Core Extractors
# ==============================

def extract_skills(text: str) -> List[str]:
    """Extract skills from resume text with deduplication."""
    found_skills = set()
    text_lower = text.lower()

    for skill in SKILL_KEYWORDS:
        # Use word boundaries for better matching
        if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
            found_skills.add(skill)

    return sorted(list(found_skills))


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


def extract_experience(text: str) -> float:
    """
    Extract years of experience from resume.
    Looks for various patterns like "5 years", "5+ years", etc.
    """
    # Pattern for explicit years mention
    patterns = [
        r'(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience',
        r'experience\s*:\s*(\d+)\+?\s*(?:years?|yrs?)',
        r'(\d+)\+?\s*(?:years?|yrs?)',
    ]

    max_years = 0
    for pattern in patterns:
        matches = re.findall(pattern, text.lower())
        if matches:
            max_years = max(max_years, max(int(m) for m in matches))

    return float(max_years) if max_years > 0 else 0.0


def extract_education(text: str) -> Optional[str]:
    """
    Extract highest education level from resume.
    Returns the highest degree found with confidence.
    """
    text_lower = text.lower()
    highest_level = None
    priority = 0  # Higher priority = higher education level

    education_priority = {
        "PhD": 4,
        "Master's Degree": 3,
        "MBA": 3,
        "Bachelor's Degree": 2,
        "Associate Degree": 1,
        "Diploma": 1
    }

    for keyword, degree in EDUCATION_KEYWORDS.items():
        if keyword in text_lower:
            current_priority = education_priority.get(degree, 0)
            if current_priority > priority:
                priority = current_priority
                highest_level = degree

    return highest_level


# ==============================
# Intelligence Scores
# ==============================

def compute_learning_velocity(text: str) -> str:
    """
    Measure learning velocity based on action verbs and project descriptions.
    Returns: High, Medium, or Low
    """
    count = sum(1 for word in LEARNING_WORDS if word in text.lower())

    # Scaled thresholds based on expanded learning vocabulary
    if count >= 8:
        return "High"
    elif count >= 4:
        return "Medium"
    return "Low"


def compute_role_match(resume_text: str, target_role: str, skills: List[str]) -> float:
    """
    Smart hybrid role matching using:
    - Semantic TF-IDF similarity
    - Skill overlap boost
    - Keyword matching

    Returns: Score between 0-100
    """
    if not target_role or not target_role.strip():
        return 50.0  # Neutral score when no role specified

    try:
        # Semantic similarity using TF-IDF
        corpus = [resume_text, target_role.lower()]
        vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=100,
            ngram_range=(1, 2)  # Consider bigrams too
        )
        tfidf_matrix = vectorizer.fit_transform(corpus)

        semantic_score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0] * 100

    except Exception as e:
        logger.warning(f"TF-IDF computation failed: {e}")
        semantic_score = 30.0  # Safe fallback

    # Skill overlap bonus
    role_words = set(target_role.lower().split())
    resume_skills = set(skills)
    skill_overlap = len(role_words.intersection(resume_skills))
    skill_bonus = min(25, skill_overlap * 8)  # Max 25 point bonus

    # Weighted final score
    # 60% semantic, 40% skill match
    final_score = (0.6 * semantic_score) + (0.4 * (50 + skill_bonus))

    # Ensure score is within bounds
    return round(min(100, max(0, final_score)), 2)


def compute_consistency_score(skills: List[str], experience_years: float) -> float:
    """
    Cross-document consistency analysis (paper §IV.A).
    Detects contradictions between claimed skills and experience level.
    Deducts points per detected inconsistency.
    """
    score = 100.0
    skills_lower = [s.lower() for s in skills]

    # Check 1: Senior skills with very low experience
    senior_skills = [
        'kubernetes', 'terraform', 'system design', 'distributed systems',
        'kafka', 'grpc', 'microservices', 'architect'
    ]
    has_senior = any(s in skills_lower for s in senior_skills)
    if has_senior and experience_years < 1.5:
        score -= 20

    # Check 2: Too many skills for experience level
    expected_max_skills = max(6, experience_years * 4)
    if len(skills) > expected_max_skills:
        score -= 12

    # Check 3: Advanced tools without foundational skills
    advanced = {'kubernetes', 'terraform', 'kafka', 'pytorch', 'tensorflow'}
    foundational = {'python', 'javascript', 'java', 'git', 'sql', 'linux'}
    if bool(advanced & set(skills_lower)) and not bool(foundational & set(skills_lower)):
        score -= 15

    # Check 4: High experience but almost no skills detected
    if experience_years >= 3 and len(skills) < 4:
        score -= 18

    return round(max(30.0, score), 2)


def validate_skills_from_text(skills: List[str], text_lower: str) -> List[dict]:
    """
    Evidence-backed skill validation (paper §IV.B).
    Classifies each skill as Valid / Partial / Unverified
    based on contextual evidence in the resume text.
    """
    ACTION_VERBS = [
        'built', 'developed', 'designed', 'implemented', 'deployed',
        'created', 'architected', 'led', 'managed', 'used', 'integrated',
        'automated', 'optimised', 'optimized', 'migrated', 'scaled',
        'wrote', 'delivered', 'maintained', 'configured', 'set up',
    ]
    validated = []
    for skill in skills:
        sl = skill.lower()
        idx = text_lower.find(sl)
        if idx == -1:
            validated.append({'skill': skill, 'status': 'Unverified'})
            continue
        window_start = max(0, idx - 60)
        window_end = min(len(text_lower), idx + len(sl) + 60)
        window = text_lower[window_start:window_end]
        has_action = any(verb in window for verb in ACTION_VERBS)
        if has_action:
            validated.append({'skill': skill, 'status': 'Valid'})
        else:
            count = text_lower.count(sl)
            if count >= 2:
                validated.append({'skill': skill, 'status': 'Partial'})
            else:
                validated.append({'skill': skill, 'status': 'Unverified'})
    return validated


def compute_skill_validation_score(skills: List[str], learning_velocity: str) -> float:
    """
    Validate skills based on quantity and learning indicators.
    """
    base_score = 40

    # Skill count bonus (max 40 points)
    skill_bonus = min(40, len(skills) * 4)

    # Learning velocity bonus (max 20 points)
    velocity_bonus = {"High": 20, "Medium": 10, "Low": 5}.get(learning_velocity, 5)

    total = base_score + skill_bonus + velocity_bonus
    return round(min(100, total), 2)


def compute_resume_strength_score(skills: List[str], education: Optional[str],
                                  experience_years: float) -> float:
    """
    Overall resume strength based on completeness and quality.
    """
    base_score = 30

    # Skills bonus (max 35 points)
    skill_bonus = min(35, len(skills) * 3)

    # Education bonus (max 20 points)
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

    # Experience bonus (max 15 points)
    experience_bonus = min(15, experience_years * 2)

    total = base_score + skill_bonus + education_bonus + experience_bonus
    return round(min(100, total), 2)


def compute_final_fit(role_score: float) -> str:
    """Categorize candidate fit based on role match score."""
    if role_score >= 70:
        return "High"
    elif role_score >= 45:
        return "Medium"
    return "Low"


def generate_career_trajectory(skills: List[str], learning_velocity: str,
                               experience_years: float) -> str:
    """Generate a meaningful career trajectory summary."""
    skill_count = len(skills)

    if skill_count >= 15:
        skill_level = "extensive"
    elif skill_count >= 8:
        skill_level = "strong"
    else:
        skill_level = "developing"

    return (
        f"Candidate demonstrates {skill_level} technical expertise with "
        f"{skill_count} identified skills, {learning_velocity.lower()} learning velocity, "
        f"and {experience_years:.1f} years of experience."
    )


# ==============================
# ✅ MAIN ANALYSIS FUNCTION
# ==============================

def analyze_resume(file_path: str, target_role: str = "") -> Dict:
    """
    Main function to analyze a resume PDF and extract comprehensive insights.

    Args:
        file_path: Path to the PDF resume file
        target_role: Target job role for matching (optional)

    Returns:
        Dict containing all analysis results

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is not a PDF or contains no text
        Exception: For other processing errors
    """
    try:
        # Extract text (both lowercase and original case)
        text_lower, text_original = extract_text_from_pdf(file_path)

        # Extract basic information
        name = extract_name(text_original)
        email = extract_email(text_original)
        phone = extract_phone(text_original)

        # Extract skills and learning indicators
        skills = extract_skills(text_lower)
        learning_velocity = compute_learning_velocity(text_lower)

        # Extract experience and education
        experience_years = extract_experience(text_lower)
        education = extract_education(text_lower)

        # Compute role matching scores
        role_score = compute_role_match(text_lower, target_role, skills)
        final_fit = compute_final_fit(role_score)

        # Compute additional scores
        consistency_score = compute_consistency_score(skills, experience_years)
        skill_validation_score = compute_skill_validation_score(skills, learning_velocity)
        resume_strength_score = compute_resume_strength_score(skills, education, experience_years)

        # Evidence-backed skill validation (paper §IV.B)
        validated_skills = validate_skills_from_text(skills, text_lower)
        valid_count = sum(1 for v in validated_skills if v['status'] == 'Valid')
        # Override skill_validation_score with evidence-based score
        if validated_skills:
            skill_validation_score = round((valid_count / len(validated_skills)) * 100, 2)

        # Generate career insights
        career_trajectory = generate_career_trajectory(skills, learning_velocity, experience_years)

        # Identify missing skills (from top skills not in resume)
        missing_skills = [s for s in SKILL_KEYWORDS[:50] if s not in skills][:8]

        # Generate explainability text
        explainability = (
            f"Matched {len(skills)} key skills with {role_score}% role relevance. "
            f"Profile shows {learning_velocity.lower()} learning velocity with "
            f"{experience_years:.1f} years of experience."
        )

        # Profile summary
        profile_summary = (
            f"{name or 'Candidate'} - {education or 'Education not specified'} | "
            f"{len(skills)} skills | {experience_years:.1f} years experience"
        )

        logger.info(f"Successfully analyzed resume: {name or 'Unknown'}")

        return {
            # Basic Information
            "name": name,
            "email": email,
            "phone": phone,

            # Skills and Learning
            "skills": skills,
            "learning_velocity": learning_velocity,
            "missing_skills": missing_skills,

            # Experience and Education
            "experience_years": experience_years,
            "education": education,

            # Role Matching
            "role_match_score": role_score,
            "final_fit": final_fit,

            # Quality Scores
            "consistency_score": consistency_score,
            "skill_validation_score": skill_validation_score,
            "resume_strength_score": resume_strength_score,

            # Insights
            "career_trajectory": career_trajectory,
            "profile_summary": profile_summary,
            "explainability": explainability,

            # Evidence-backed skill validation (paper §IV.B)
            "validated_skills": validated_skills,
        }

    except FileNotFoundError as e:
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

# GitHub API Configuration
GITHUB_API_BASE = "https://api.github.com"
GITHUB_SEARCH_USERS = f"{GITHUB_API_BASE}/search/users"
GITHUB_USER_REPOS = f"{GITHUB_API_BASE}/users/{{username}}/repos"
GITHUB_USER_PROFILE = f"{GITHUB_API_BASE}/users/{{username}}"

# Rate limiting and timeout configs
GITHUB_REQUEST_TIMEOUT = 10  # seconds
GITHUB_RATE_LIMIT_DELAY = 1  # seconds between requests
MAX_REPOS_TO_ANALYZE = 30  # limit repos per user for performance


def _make_github_request(url: str, params: Optional[Dict] = None,
                         timeout: int = GITHUB_REQUEST_TIMEOUT) -> Optional[Dict]:
    """
    Make a request to GitHub API with error handling and rate limiting.

    Args:
        url: GitHub API endpoint URL
        params: Query parameters
        timeout: Request timeout in seconds

    Returns:
        JSON response as dict or None on error
    """
    try:
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'NeuroHire-Recruiter-Platform'
        }

        # Add authentication if available (optional but recommended)
        github_token = os.environ.get('GITHUB_TOKEN')
        if github_token:
            headers['Authorization'] = f'token {github_token}'

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=timeout
        )

        # Check rate limit
        if response.status_code == 403:
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', '0')
            if rate_limit_remaining == '0':
                reset_time = response.headers.get('X-RateLimit-Reset', 'unknown')
                logger.warning(f"GitHub API rate limit exceeded. Resets at: {reset_time}")
                return None

        # Raise for bad status codes
        response.raise_for_status()

        # Respect rate limiting
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
    """
    Extract programming languages from a user's repositories.

    Args:
        username: GitHub username
        max_repos: Maximum number of repos to analyze

    Returns:
        Dict of language -> byte count
    """
    languages_aggregate = {}

    try:
        # Get user's repositories
        repos_url = GITHUB_USER_REPOS.format(username=username)
        params = {
            'sort': 'updated',
            'direction': 'desc',
            'per_page': max_repos
        }

        repos_data = _make_github_request(repos_url, params)
        if not repos_data:
            return languages_aggregate

        # Aggregate languages from repos
        for repo in repos_data[:max_repos]:
            if repo.get('fork', False):
                continue  # Skip forked repos

            language = repo.get('language')
            if language:
                languages_aggregate[language] = languages_aggregate.get(language, 0) + 1

        return languages_aggregate

    except Exception as e:
        logger.error(f"Failed to extract languages for user {username}: {str(e)}")
        return languages_aggregate


def _get_top_languages(languages_dict: Dict[str, int], top_n: int = 5) -> List[str]:
    """
    Get top N languages sorted by usage count.

    Args:
        languages_dict: Dict of language -> count
        top_n: Number of top languages to return

    Returns:
        List of top language names
    """
    if not languages_dict:
        return []

    sorted_languages = sorted(
        languages_dict.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return [lang for lang, _ in sorted_languages[:top_n]]


def _format_github_user(user_data: Dict, languages: List[str]) -> Dict:
    """
    Format GitHub user data into clean structured response.

    Args:
        user_data: Raw GitHub user data
        languages: List of programming languages

    Returns:
        Formatted user dict
    """
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
    """
    Calculate a profile quality score for GitHub user.

    Args:
        user_data: GitHub user data
        languages: List of languages

    Returns:
        Score between 0-100
    """
    score = 0.0

    # Public repos (max 30 points)
    repos = user_data.get('public_repos', 0)
    score += min(30, repos * 1.5)

    # Followers (max 25 points)
    followers = user_data.get('followers', 0)
    score += min(25, followers * 0.5)

    # Languages diversity (max 20 points)
    score += min(20, len(languages) * 4)

    # Has bio (10 points)
    if user_data.get('bio'):
        score += 10

    # Has company (8 points)
    if user_data.get('company'):
        score += 8

    # Has location (7 points)
    if user_data.get('location'):
        score += 7

    return round(min(100, score), 2)


def github_search_service(query: str, max_results: int = 10) -> Dict:
    """
    Search GitHub users by skills/keywords with comprehensive data extraction.

    This is a production-ready service that:
    - Searches GitHub users via REST API
    - Handles pagination and rate limiting
    - Extracts profile data and programming languages
    - Returns clean structured JSON
    - Includes proper error handling and timeouts

    Args:
        query: Search query (e.g., "python django", "machine learning")
        max_results: Maximum number of results to return (default: 10, max: 100)

    Returns:
        Dict containing:
        - success: bool
        - data: List of formatted user dicts
        - total_count: Total matching users on GitHub
        - query: Original search query
        - error: Error message if failed

    Example:
        >>> result = github_search_service("python developer", max_results=5)
        >>> if result['success']:
        >>>     for user in result['data']:
        >>>         print(f"{user['username']}: {user['top_languages']}")
    """
    try:
        # Validate inputs
        if not query or not query.strip():
            return {
                'success': False,
                'error': 'Search query is required',
                'data': [],
                'total_count': 0,
                'query': query
            }

        # Limit max results to reasonable number
        max_results = min(max_results, 100)

        logger.info(f"GitHub search initiated: query='{query}', max_results={max_results}")

        # Search for users
        search_params = {
            'q': query,
            'per_page': max_results,
            'sort': 'followers',  # Sort by followers for quality results
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

        # Process each user
        formatted_users = []
        for user in users:
            username = user.get('login')
            if not username:
                continue

            # Get detailed user profile
            profile_url = GITHUB_USER_PROFILE.format(username=username)
            user_details = _make_github_request(profile_url)

            if not user_details:
                # Use basic data if detailed fetch fails
                user_details = user

            # Extract languages from repositories
            languages_dict = _extract_languages_from_repos(username)
            top_languages = _get_top_languages(languages_dict)

            # Format user data
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