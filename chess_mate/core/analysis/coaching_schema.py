"""
Coaching report JSON schema for OpenAI structured outputs.

This schema is locked per PRD section 11. Do not modify without updating the PRD document.
"""

# Exact schema from PRD section 11 — canonical reference
BATCH_COACHING_REPORT_SCHEMA = {
    "name": "batch_coaching_report",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "executive_summary",
            "coaching_narrative",
            "top_3_priorities",
            "training_plan",
            "one_thing_to_do_today",
        ],
        "properties": {
            "executive_summary": {"type": "string"},
            "coaching_narrative": {
                "type": "object",
                "additionalProperties": False,
                "required": ["opening", "middlegame", "endgame"],
                "properties": {
                    "opening": {"type": "string"},
                    "middlegame": {"type": "string"},
                    "endgame": {"type": "string"},
                },
            },
            "top_3_priorities": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "rank",
                        "title",
                        "why_it_matters",
                        "how_to_fix",
                        "specific_drill",
                        "estimated_study_hours",
                    ],
                    "properties": {
                        "rank": {"type": "integer", "enum": [1, 2, 3]},
                        "title": {"type": "string"},
                        "why_it_matters": {"type": "string"},
                        "how_to_fix": {"type": "string"},
                        "specific_drill": {"type": "string"},
                        "estimated_study_hours": {"type": "number", "minimum": 0},
                    },
                },
            },
            "training_plan": {
                "type": "object",
                "additionalProperties": False,
                "required": ["week_1", "week_2", "week_3", "week_4"],
                "properties": {
                    "week_1": {"type": "string"},
                    "week_2": {"type": "string"},
                    "week_3": {"type": "string"},
                    "week_4": {"type": "string"},
                },
            },
            "one_thing_to_do_today": {"type": "string"},
        },
    },
}
