{
  "name": "Interview",
  "type": "object",
  "properties": {
    "candidate_id": {
      "type": "string",
      "description": "Reference to candidate"
    },
    "candidate_name": {
      "type": "string",
      "description": "Candidate name for display"
    },
    "role": {
      "type": "string",
      "description": "Role being interviewed for"
    },
    "scheduled_date": {
      "type": "string",
      "format": "date-time",
      "description": "Interview date and time"
    },
    "interview_link": {
      "type": "string",
      "description": "Unique interview link"
    },
    "status": {
      "type": "string",
      "enum": [
        "scheduled",
        "completed",
        "cancelled",
        "no_show"
      ],
      "default": "scheduled"
    },
    "notes": {
      "type": "string",
      "description": "Interview notes"
    }
  },
  "required": [
    "candidate_name",
    "scheduled_date"
  ]
}