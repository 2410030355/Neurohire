{
  "name": "WaitlistEntry",
  "type": "object",
  "properties": {
    "candidate_id": {
      "type": "string",
      "description": "Reference to candidate"
    },
    "candidate_name": {
      "type": "string",
      "description": "Candidate name"
    },
    "role": {
      "type": "string",
      "description": "Role considered for"
    },
    "reason": {
      "type": "string",
      "description": "Why waitlisted"
    },
    "priority": {
      "type": "string",
      "enum": [
        "low",
        "medium",
        "high"
      ],
      "default": "medium"
    },
    "match_score": {
      "type": "number",
      "description": "Overall match score"
    }
  },
  "required": [
    "candidate_name"
  ]
}