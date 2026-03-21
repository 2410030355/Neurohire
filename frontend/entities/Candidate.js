{
  "name": "Candidate",
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "Full name of the candidate"
    },
    "email": {
      "type": "string",
      "description": "Email address"
    },
    "phone": {
      "type": "string",
      "description": "Phone number"
    },
    "resume_url": {
      "type": "string",
      "description": "URL of uploaded resume file"
    },
    "source": {
      "type": "string",
      "enum": [
        "resume_upload",
        "github_search",
        "job_portal_search"
      ],
      "description": "How candidate was sourced"
    },
    "status": {
      "type": "string",
      "enum": [
        "new",
        "analyzed",
        "scheduled",
        "waitlisted",
        "rejected",
        "hired"
      ],
      "default": "new"
    },
    "target_role": {
      "type": "string",
      "description": "Role being evaluated for"
    },
    "consistency_score": {
      "type": "number",
      "description": "Cross-document consistency score 0-100"
    },
    "skill_validation_score": {
      "type": "number",
      "description": "Evidence-backed skill validation score 0-100"
    },
    "learning_velocity": {
      "type": "string",
      "enum": [
        "Low",
        "Medium",
        "High"
      ],
      "description": "Learning velocity assessment"
    },
    "career_trajectory": {
      "type": "string",
      "description": "Career trajectory analysis text"
    },
    "role_match_score": {
      "type": "number",
      "description": "Role-skill match score 0-100"
    },
    "final_fit": {
      "type": "string",
      "enum": [
        "Low",
        "Medium",
        "High"
      ],
      "description": "Final fit label"
    },
    "explainability": {
      "type": "string",
      "description": "Why this rating - explanation text"
    },
    "skills": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "List of validated skills"
    },
    "experience_years": {
      "type": "number",
      "description": "Years of experience"
    },
    "education": {
      "type": "string",
      "description": "Education summary"
    },
    "github_url": {
      "type": "string",
      "description": "GitHub profile URL"
    },
    "repo_score": {
      "type": "number",
      "description": "GitHub activity/repo score"
    },
    "profile_summary": {
      "type": "string",
      "description": "Brief profile summary"
    },
    "resume_strength_score": {
      "type": "number",
      "description": "Resume strength score 0-100"
    },
    "improvement_suggestions": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Resume improvement suggestions"
    },
    "missing_skills": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Skills missing for target role"
    }
  },
  "required": [
    "name"
  ]
}