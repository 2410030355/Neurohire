{
  "name": "AIDecisionLog",
  "type": "object",
  "properties": {
    "candidate_id": {
      "type": "string"
    },
    "candidate_name": {
      "type": "string"
    },
    "ai_recommendation": {
      "type": "string",
      "enum": [
        "hire",
        "waitlist",
        "reject"
      ],
      "description": "AI's recommendation"
    },
    "recruiter_decision": {
      "type": "string",
      "enum": [
        "hire",
        "waitlist",
        "reject"
      ],
      "description": "Recruiter's actual decision"
    },
    "ai_confidence": {
      "type": "number",
      "description": "AI confidence in recommendation 0-100"
    },
    "reason": {
      "type": "string",
      "description": "Recruiter reason for override"
    },
    "is_agreement": {
      "type": "boolean",
      "description": "Whether AI and recruiter agreed"
    }
  },
  "required": [
    "candidate_name",
    "ai_recommendation",
    "recruiter_decision"
  ]
}