{
  "name": "MockInterview",
  "type": "object",
  "properties": {
    "role": {
      "type": "string",
      "description": "Role being practiced for"
    },
    "questions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "question": {
            "type": "string"
          },
          "answer": {
            "type": "string"
          },
          "confidence_score": {
            "type": "number"
          },
          "clarity_score": {
            "type": "number"
          },
          "filler_words_count": {
            "type": "number"
          },
          "speaking_pace": {
            "type": "string"
          },
          "knowledge_relevance": {
            "type": "number"
          }
        }
      },
      "description": "Interview Q&A with analysis"
    },
    "overall_confidence": {
      "type": "number",
      "description": "Overall confidence score 0-100"
    },
    "overall_clarity": {
      "type": "number",
      "description": "Overall clarity score 0-100"
    },
    "total_filler_words": {
      "type": "number"
    },
    "avg_speaking_pace": {
      "type": "string"
    },
    "improvements": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "What to improve"
    },
    "status": {
      "type": "string",
      "enum": [
        "in_progress",
        "completed"
      ],
      "default": "in_progress"
    }
  },
  "required": [
    "role"
  ]
}