{
  "name": "JobPosting",
  "type": "object",
  "properties": {
    "title": {
      "type": "string",
      "description": "Job title"
    },
    "company": {
      "type": "string",
      "description": "Company name"
    },
    "description": {
      "type": "string",
      "description": "Job description"
    },
    "requirements": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Job requirements"
    },
    "skills_required": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Required skills"
    },
    "experience_range": {
      "type": "string",
      "description": "Experience range e.g. 2-5 years"
    },
    "location": {
      "type": "string"
    },
    "job_type": {
      "type": "string",
      "enum": [
        "full_time",
        "part_time",
        "internship",
        "contract"
      ],
      "default": "full_time"
    },
    "salary_range": {
      "type": "string"
    },
    "apply_url": {
      "type": "string",
      "description": "Direct link to apply for the job"
    },
    "status": {
      "type": "string",
      "enum": [
        "active",
        "closed",
        "draft"
      ],
      "default": "active"
    }
  },
  "required": [
    "title"
  ]
}