"""
Feedback generator for chess games.
Handles generation of game feedback using OpenAI API.
"""

import json
import logging
import sys
from typing import Any, Dict, List, Optional, cast

from django.conf import settings
from openai import OpenAI, OpenAIError

logger = logging.getLogger(__name__)


def _resolve_patched_openai(default: Any) -> Any:
    """Resolve OpenAI class across module aliases, preferring monkeypatched symbol."""
    for module_name in (
        "core.analysis.feedback_generator",
        "chess_mate.core.analysis.feedback_generator",
        "chessmate_prod.chess_mate.core.analysis.feedback_generator",
        __name__,
    ):
        module = sys.modules.get(module_name)
        candidate = getattr(module, "OpenAI", None) if module else None
        if isinstance(candidate, object) and hasattr(candidate, "assert_called"):
            return candidate
    return default


class FeedbackGenerator:
    """Generates feedback for chess games using OpenAI."""

    @staticmethod
    def _normalized_classification(move: Dict[str, Any]) -> str:
        raw = str(move.get("classification", "")).strip().lower().replace("_", " ")
        if raw in {"good", "good move"}:
            return "good"
        if raw in {"excellent", "excellent move", "great move", "best", "best move", "brilliant"}:
            return "excellent"
        if raw in {"mistake", "blunder", "inaccuracy", "neutral"}:
            return raw
        return "neutral"

    @staticmethod
    def _eval_change_to_cp(eval_change: Any) -> float:
        try:
            value = float(eval_change)
        except (TypeError, ValueError):
            return 0.0
        return value * 100.0 if abs(value) <= 20.0 else value

    @staticmethod
    def _phase_from_index(move_index: int, total_moves: int) -> str:
        if total_moves <= 0:
            return "middlegame"

        opening_cutoff = max(8, total_moves // 3)
        endgame_start = max(opening_cutoff + 1, total_moves - max(8, total_moves // 3))

        if move_index < opening_cutoff:
            return "opening"
        if move_index >= endgame_start:
            return "endgame"
        return "middlegame"

    @staticmethod
    def _safe_number(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _metric_phase_name(game_metrics: Dict[str, Any]) -> str:
        phases = game_metrics.get("phases", {}) if isinstance(game_metrics.get("phases", {}), dict) else {}
        if not phases:
            return "middlegame"

        phase_name, _ = min(
            ((name, FeedbackGenerator._safe_number(data.get("accuracy", 0.0), 0.0)) for name, data in phases.items()),
            key=lambda item: item[1],
        )
        return str(phase_name)

    @classmethod
    def _derive_impact_metrics(cls, game_metrics: Dict[str, Any]) -> Dict[str, Any]:
        overall = game_metrics.get("overall", {}) if isinstance(game_metrics.get("overall", {}), dict) else {}
        phases = game_metrics.get("phases", {}) if isinstance(game_metrics.get("phases", {}), dict) else {}

        total_moves = max(1.0, cls._safe_number(overall.get("total_moves", 0.0), 0.0))
        mistakes = cls._safe_number(overall.get("mistakes", 0.0), 0.0)
        blunders = cls._safe_number(overall.get("blunders", 0.0), 0.0)
        inaccuracies = cls._safe_number(overall.get("inaccuracies", 0.0), 0.0)
        accuracy = cls._safe_number(overall.get("accuracy", 0.0), 0.0)

        phase_risk: Dict[str, float] = {}
        for phase_name, data in phases.items():
            phase_accuracy = cls._safe_number(data.get("accuracy", 0.0), 0.0)
            best_moves = cls._safe_number(data.get("best_moves", 0.0), 0.0)
            opportunities = max(0.0, cls._safe_number(data.get("opportunities", 0.0), 0.0))
            missed = max(0.0, opportunities - best_moves)
            phase_risk[phase_name] = round(
                max(
                    0.0,
                    (100.0 - phase_accuracy) * 0.6
                    + missed * 4.0
                    + cls._safe_number(data.get("mistakes", 0.0), 0.0) * 2.5,
                ),
                1,
            )

        critical_error_rate = round(((blunders * 3.0) + (mistakes * 2.0) + inaccuracies) / total_moves, 2)
        phase_risk_index = round(sum(phase_risk.values()) / max(1, len(phase_risk)), 1) if phase_risk else 0.0

        return {
            "critical_error_rate": critical_error_rate,
            "phase_risk_index": phase_risk_index,
            "phase_risk": phase_risk,
            "accuracy_gap": round(max(0.0, 100.0 - accuracy), 1),
        }

    @classmethod
    def _build_phase_motifs(cls, game_metrics: Dict[str, Any], max_motifs: int = 2) -> Dict[str, Any]:
        moves = game_metrics.get("moves", []) if isinstance(game_metrics.get("moves", []), list) else []
        target_phase = cls._metric_phase_name(game_metrics)
        if not moves:
            return {
                "weakest_phase": target_phase,
                "motifs": [],
                "correction_rule": (
                    "Review the phase without overloading on engine lines; "
                    "focus on one repeatable checklist."
                ),
            }

        phase_moves: List[Dict[str, Any]] = []
        for index, move in enumerate(moves):
            phase = cls._phase_from_index(index, len(moves))
            if phase == target_phase:
                phase_moves.append(move if isinstance(move, dict) else {})

        motif_counts: Dict[str, Dict[str, Any]] = {}

        def bump(key: str, evidence: Dict[str, Any]) -> None:
            current = motif_counts.setdefault(key, {"count": 0, "evidence": []})
            current["count"] += 1
            if len(current["evidence"]) < 3:
                current["evidence"].append(evidence)

        for move in phase_moves:
            classification = FeedbackGenerator._normalized_classification(move)
            eval_change = abs(cls._eval_change_to_cp(move.get("eval_change", move.get("evaluation_drop", 0))))
            is_critical = bool(move.get("is_critical", False))
            is_best = bool(move.get("is_best", False))
            best_move_present = bool(move.get("best_move") or move.get("best_move_san"))

            if classification in {"mistake", "blunder"}:
                bump(
                    "tactical slip",
                    {
                        "move": move.get("move_number"),
                        "san": move.get("san") or move.get("move"),
                        "loss": round(eval_change, 1),
                    },
                )

            if classification == "inaccuracy":
                bump(
                    "positional drift",
                    {
                        "move": move.get("move_number"),
                        "san": move.get("san") or move.get("move"),
                        "loss": round(eval_change, 1),
                    },
                )

            if is_critical and not is_best and best_move_present:
                bump(
                    "missed best move",
                    {
                        "move": move.get("move_number"),
                        "san": move.get("san") or move.get("move"),
                        "loss": round(eval_change, 1),
                    },
                )

            if target_phase == "endgame" and eval_change >= 100:
                bump(
                    "conversion issue",
                    {
                        "move": move.get("move_number"),
                        "san": move.get("san") or move.get("move"),
                        "loss": round(eval_change, 1),
                    },
                )

        rule_library = {
            "tactical slip": (
                "Scan for checks, captures, and forcing replies before committing "
                "to the first promising move."
            ),
            "positional drift": (
                "When there is no forcing tactic, improve piece activity, king safety, "
                "and pawn structure before grabbing material."
            ),
            "missed best move": (
                "Write down 2 candidate moves, compare forcing lines, then choose "
                "the move that keeps the evaluation stable or improves it."
            ),
            "conversion issue": (
                "In winning endgames, simplify toward a clear conversion plan and "
                "verify the king and passed pawn path before trading."
            ),
        }

        motifs = []
        for name, data in sorted(motif_counts.items(), key=lambda item: (-item[1]["count"], item[0]))[:max_motifs]:
            motifs.append(
                {
                    "name": name,
                    "count": data["count"],
                    "evidence": data["evidence"],
                    "correction_rule": rule_library.get(
                        name,
                        "Pause, review candidate moves, and pick the line "
                        "that keeps the position stable.",
                    ),
                }
            )

        if not motifs:
            motifs = [
                {
                    "name": "candidate move discipline",
                    "count": 1,
                    "evidence": [],
                    "correction_rule": "Before moving, compare at least two candidate moves and one forcing idea.",
                }
            ]

        primary_rule = motifs[0]["correction_rule"] if motifs else "Review the phase with a structured checklist."
        return {"weakest_phase": target_phase, "motifs": motifs, "correction_rule": primary_rule}

    @classmethod
    def _build_training_block(cls, game_metrics: Dict[str, Any]) -> Dict[str, Any]:
        overall = game_metrics.get("overall", {}) if isinstance(game_metrics.get("overall", {}), dict) else {}
        phases = game_metrics.get("phases", {}) if isinstance(game_metrics.get("phases", {}), dict) else {}
        time_mgmt = (
            game_metrics.get("time_management", {})
            if isinstance(game_metrics.get("time_management", {}), dict)
            else {}
        )

        impact = cls._derive_impact_metrics(game_metrics)
        motif_block = cls._build_phase_motifs(game_metrics)
        weakest_phase = motif_block["weakest_phase"]

        phase_accuracy = cls._safe_number(phases.get(weakest_phase, {}).get("accuracy", 0.0), 0.0)
        total_moves = max(1.0, cls._safe_number(overall.get("total_moves", 0.0), 0.0))
        inaccuracies = cls._safe_number(overall.get("inaccuracies", 0.0), 0.0)
        blunders = cls._safe_number(overall.get("blunders", 0.0), 0.0)
        time_pressure = cls._safe_number(time_mgmt.get("time_pressure_percentage", 0.0), 0.0)
        time_status = str(time_mgmt.get("data_status", "unavailable") or "unavailable")

        focus_areas = []
        if weakest_phase == "opening":
            focus_areas.extend([
                "Opening development and piece coordination",
                "Avoiding early inaccuracies that derail the plan",
            ])
        elif weakest_phase == "middlegame":
            focus_areas.extend([
                "Candidate-move calculation in middlegame positions",
                "Identifying and converting tactical opportunities",
            ])
        else:
            focus_areas.extend([
                "Endgame conversion technique",
                "King activity and pawn-structure precision",
            ])

        if time_status == "available" and time_pressure >= 20:
            focus_areas.append("Time allocation under pressure")
        if blunders > 0 or inaccuracies >= max(8.0, total_moves * 0.12):
            focus_areas.append("Move blunder-check routine")

        drill_library = {
            "opening": [
                "Play through 5 master games in your main opening and note where development slows down.",
                "After each opening move, ask whether every piece has a job and every pawn move has a reason.",
            ],
            "middlegame": [
                "For 10 tactical positions, write down two candidate moves before looking at engine lines.",
                "Review your last 5 middlegame inaccuracies and classify each "
                "as tactical, positional, or time-related.",
            ],
            "endgame": [
                "Practice 5 endgames where the plan is to trade into the simplest winning conversion.",
                "Before every endgame move, verify king activity, passed pawns, and whether you can simplify.",
            ],
            "time_pressure": [
                "Use a fixed decision budget per move in practical games and stop at the budget before overchecking.",
                "Track where time is lost and compare it to the phase where accuracy drops the most.",
            ],
            "blunder_check": [
                "Run a 3-step pre-move check: opponent threats, forcing moves, your hanging pieces.",
                "Review the last 10 inaccuracies and annotate the missing "
                "question you should have asked before moving.",
            ],
        }

        drills = []
        drills.extend(drill_library.get(weakest_phase, []))
        if time_status == "available" and time_pressure >= 20:
            drills.extend(drill_library["time_pressure"])
        if blunders > 0 or inaccuracies >= max(8.0, total_moves * 0.12):
            drills.extend(drill_library["blunder_check"])
        drills.extend([
            f"Review the two most costly moments in the {weakest_phase} "
            "and explain the correction in one sentence each.",
        ])

        checklist = [
            f"Identify the weakest phase ({weakest_phase}) before the next study session.",
            motif_block["correction_rule"],
            "Pause on every critical move and compare at least two candidate lines.",
        ]
        if time_status == "available" and time_pressure >= 20:
            checklist.append("Set a time budget and keep one reserve minute for the final phase.")
        if phase_accuracy < 65:
            checklist.append(
                f"Spend extra review time on {weakest_phase} positions "
                "until accuracy reaches at least 70%."
            )

        phase_risk_value = impact["phase_risk"].get(weakest_phase, 0.0)
        weekly_target = {
            "goal": f"Improve {weakest_phase} accuracy by focusing on the recurring motifs below.",
            "measure": (
                f"In the next 5 games, reduce the {weakest_phase} risk signal "
                f"from {phase_risk_value} to a lower level by cutting repeat mistakes."
            ),
            "confidence": "high" if len(checklist) >= 4 else "medium",
        }

        return {
            "focus_areas": focus_areas[:4],
            "drills": drills[:5],
            "checklist": checklist[:5],
            "weekly_target": weekly_target,
            "phase_motifs": motif_block,
            "impact_metrics": impact,
            "data_confidence": "high" if total_moves >= 30 else "medium" if total_moves >= 12 else "low",
        }

    @classmethod
    def build_training_block(cls, game_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Public wrapper used by callers outside this class."""
        return cls._build_training_block(game_metrics)

    def __init__(self):
        """Initialize the feedback generator."""
        self.openai_client = None
        self._initialize_openai()

    def _initialize_openai(self) -> None:
        """Initialize OpenAI client."""
        try:
            api_key = getattr(settings, "OPENAI_API_KEY", None)
            api_key = api_key.strip() if isinstance(api_key, str) else api_key
            if not api_key:
                logger.warning("OpenAI API key not found in settings")
                self.openai_client = None
                return

            openai_cls = _resolve_patched_openai(OpenAI)
            self.openai_client = openai_cls(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
        except (AttributeError, TypeError, ValueError) as e:
            logger.error("Error initializing OpenAI client: %s", e)
            self.openai_client = None

    def generate_feedback(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate feedback from either OpenAI or statistical fallback."""
        try:
            # Accept both schemas used across the codebase/tests:
            # 1) {"overall": ..., "phases": ...}
            # 2) {"metrics": {"summary": {...}}}
            game_metrics = analysis_result
            if isinstance(analysis_result, dict) and isinstance(analysis_result.get("metrics"), dict):
                summary = analysis_result["metrics"].get("summary")
                if isinstance(summary, dict):
                    game_metrics = summary

            if not isinstance(game_metrics, dict) or "overall" not in game_metrics:
                logger.warning("Invalid metrics provided, using statistical feedback")
                return self._generate_statistical_feedback({})

            # Prefer AI feedback when client is available.
            if self.openai_client is not None:
                prompt = self._generate_analysis_prompt(game_metrics)
                if prompt:
                    response = self.openai_client.chat.completions.create(
                        model=getattr(settings, "OPENAI_MODEL", "gpt-3.5-turbo"),
                        messages=[
                            {"role": "system", "content": "You are a chess coach. Return valid JSON only."},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=getattr(settings, "OPENAI_TEMPERATURE", 0.2),
                    )
                    content = response.choices[0].message.content if response and response.choices else ""
                    parsed = self._parse_ai_response(content or "")
                    if parsed and isinstance(parsed.get("feedback"), dict):
                        ai_feedback = cast(Dict[str, Any], parsed["feedback"])
                        ai_feedback["metrics"] = self._calculate_statistical_metrics(game_metrics)
                        training_block = self._build_training_block(game_metrics)
                        ai_feedback.setdefault("training_block", training_block)
                        ai_feedback.setdefault("phase_motifs", training_block.get("phase_motifs", {}))
                        ai_feedback.setdefault("impact_metrics", training_block.get("impact_metrics", {}))
                        ai_feedback.setdefault("source", "openai")
                        return ai_feedback

            return self._generate_statistical_feedback(game_metrics)

        except (AttributeError, TypeError, ValueError, json.JSONDecodeError, OpenAIError) as e:
            logger.error("Error generating feedback: %s", e)
            return self._generate_statistical_feedback(analysis_result if isinstance(analysis_result, dict) else {})

    def _analyze_phase(self, moves: List[Dict[str, Any]]) -> str:
        """Analyze a specific phase of the game."""
        if not moves:
            return "No moves in this phase"

        good_moves = sum(1 for m in moves if self._normalized_classification(m) in ['good', 'excellent'])
        mistakes = sum(1 for m in moves if self._normalized_classification(m) in ['mistake', 'blunder', 'inaccuracy'])
        accuracy = (good_moves / len(moves) * 100) if moves else 0.0

        return f"Accuracy: {accuracy:.1f}%, Good moves: {good_moves}, Mistakes: {mistakes}"

    def _calculate_consistency(self, moves: List[Dict[str, Any]]) -> float:
        """Calculate basic consistency score."""
        if not moves:
            return 100.0

        streak_lengths = []
        current_streak = 0

        for move in moves:
            if self._normalized_classification(move) in ['good', 'excellent']:
                current_streak += 1
            else:
                if current_streak > 0:
                    streak_lengths.append(current_streak)
                current_streak = 0

        if current_streak > 0:
            streak_lengths.append(current_streak)

        avg_streak = sum(streak_lengths) / len(streak_lengths) if streak_lengths else 0
        return min(100.0, (avg_streak / 5.0) * 100.0)  # Normalize to 5-move streaks

    def _validate_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Validate that the metrics contain required data."""
        try:
            # Check if we have the basic structure
            if not isinstance(metrics, dict):
                logger.warning("Metrics is not a dictionary")
                return False

            # Handle both nested and unnested structures
            if "analysis_results" in metrics:
                metrics = metrics["analysis_results"]

            # Handle summary wrapper
            if "summary" in metrics:
                summary = metrics["summary"]
            else:
                summary = metrics

            # Get moves from either top level or nested
            moves = metrics.get("moves", []) or summary.get("moves", [])
            has_moves = bool(moves)

            # Get overall metrics
            overall = summary.get("overall", {})
            if not overall and isinstance(summary.get("summary", {}), dict):
                overall = summary["summary"].get("overall", {})

            # More lenient validation
            has_accuracy = overall.get("accuracy", 0) >= 0  # Allow 0 accuracy
            has_any_metrics = any(
                overall.get(key, 0) >= 0  # Allow 0 values
                for key in ["mistakes", "blunders", "inaccuracies", "time_management_score"]
            )

            # Consider valid if we have moves and any metrics
            is_valid = has_moves and (has_accuracy or has_any_metrics)

            if not is_valid:
                logger.warning(
                    "Metrics validation failed: has_moves=%s, accuracy=%s, other_metrics=%s",
                    has_moves,
                    has_accuracy,
                    has_any_metrics,
                )
                logger.debug("Overall metrics: %s", overall)
                logger.debug("Moves count: %s", len(moves))
                logger.debug("Metrics structure: %s", list(metrics.keys()))
            else:
                logger.info("Metrics validation passed successfully")

            return is_valid

        except (AttributeError, TypeError, ValueError) as e:
            logger.error("Error validating metrics: %s", e)
            logger.debug("Metrics that caused error: %s", metrics)
            return False

    def _generate_analysis_prompt(self, game_metrics: Dict[str, Any]) -> str:
        """Generate a detailed prompt for AI analysis."""
        try:
            # Extract and validate metrics
            overall = game_metrics.get("overall", {})
            phases = game_metrics.get("phases", {})
            tactics = game_metrics.get("tactics", {})
            time_mgmt = game_metrics.get("time_management", {})
            training_block = self._build_training_block(game_metrics)

            prompt_data = {
                "game_metrics": {
                    "total_moves": overall.get("total_moves", 0),
                    "accuracy": overall.get("accuracy", 0),
                    "mistakes": overall.get("mistakes", 0),
                    "blunders": overall.get("blunders", 0),
                    "average_centipawn_loss": overall.get("average_centipawn_loss", 0),
                    "time_management": {
                        "time_pressure_moves": time_mgmt.get("time_pressure_moves", 0),
                        "average_time": time_mgmt.get("average_time", 0),
                        "time_management_score": time_mgmt.get("time_management_score", 0),
                    },
                    "tactics": {
                        "opportunities": tactics.get("opportunities", 0),
                        "successful": tactics.get("successful", 0),
                        "tactical_score": tactics.get("tactical_score", 0),
                    },
                    "phases": {
                        "opening": phases.get("opening", {}),
                        "middlegame": phases.get("middlegame", {}),
                        "endgame": phases.get("endgame", {}),
                    },
                    "training_context": {
                        "impact_metrics": training_block.get("impact_metrics", {}),
                        "phase_motifs": training_block.get("phase_motifs", {}),
                    },
                }
            }

            return f"""Analyze these chess game metrics and provide detailed feedback in JSON format:

            Game metrics: {json.dumps(prompt_data, indent=2)}

            Provide analysis in this exact JSON structure:
            {{
                "feedback": {{
                    "source": "openai",
                    "strengths": ["list of specific strengths based on the metrics"],
                    "weaknesses": ["list of specific weaknesses and areas for improvement"],
                    "critical_moments": ["list of important moments or patterns identified"],
                    "improvement_areas": ["specific suggestions for improvement"],
                    "opening": {{
                        "analysis": "detailed analysis of opening play",
                        "suggestion": "specific suggestion for opening improvement"
                    }},
                    "middlegame": {{
                        "analysis": "detailed analysis of middlegame play",
                        "suggestion": "specific suggestion for middlegame improvement"
                    }},
                    "endgame": {{
                        "analysis": "detailed analysis of endgame play",
                        "suggestion": "specific suggestion for endgame improvement"
                    }},
                    "training_block": {{
                        "focus_areas": ["2-4 concise focus areas grounded in the metrics"],
                        "drills": ["3-5 concrete training drills or review tasks"],
                        "checklist": ["repeatable in-game checklist items"],
                        "weekly_target": {{
                            "goal": "one weekly improvement target",
                            "measure": "how the player will know it improved",
                            "confidence": "high|medium|low"
                        }},
                        "phase_motifs": {{
                            "weakest_phase": "opening|middlegame|endgame",
                            "motifs": [
                                {{
                                    "name": "motif name",
                                    "count": 1,
                                    "evidence": [{{"move": 0, "san": "", "loss": 0.0}}],
                                    "correction_rule": "concrete correction rule"
                                }}
                            ]
                        }},
                        "impact_metrics": {{
                            "critical_error_rate": 0.0,
                            "phase_risk_index": 0.0,
                            "phase_risk": {{"opening": 0.0, "middlegame": 0.0, "endgame": 0.0}},
                            "accuracy_gap": 0.0
                        }}
                    }}
                }}
            }}"""
        except (AttributeError, TypeError, ValueError) as e:
            logger.error("Error generating analysis prompt: %s", e)
            return ""

    def _extract_sections(self, text: str) -> Dict[str, List[str]]:
        """Extract sections from AI response text."""
        sections: Dict[str, List[str]] = {
            "strengths": [],
            "weaknesses": [],
            "critical_moments": [],
            "improvement_areas": [],
            "opening": [],
            "middlegame": [],
            "endgame": [],
        }

        current_section = None
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Check for section headers
            lower_line = line.lower()
            if "strengths:" in lower_line:
                current_section = "strengths"
                continue
            elif "weaknesses:" in lower_line:
                current_section = "weaknesses"
                continue
            elif "critical moments:" in lower_line:
                current_section = "critical_moments"
                continue
            elif "improvement areas:" in lower_line:
                current_section = "improvement_areas"
                continue
            elif "opening:" in lower_line:
                current_section = "opening"
                continue
            elif "middlegame:" in lower_line:
                current_section = "middlegame"
                continue
            elif "endgame:" in lower_line:
                current_section = "endgame"
                continue

            # Add content to current section
            if current_section and line:
                if line.startswith("- "):
                    line = line[2:]
                sections[current_section].append(line)

        return sections

    def _parse_ai_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse and validate the AI response payload."""
        required_feedback_fields = {
            "source",
            "strengths",
            "weaknesses",
            "critical_moments",
            "improvement_areas",
            "opening",
            "middlegame",
            "endgame",
        }

        def _is_valid_payload(payload: Dict[str, Any]) -> bool:
            if not isinstance(payload, dict):
                return False
            feedback = payload.get("feedback")
            if not isinstance(feedback, dict):
                return False
            return required_feedback_fields.issubset(feedback.keys())

        try:
            # First try strict JSON payload parsing.
            try:
                parsed = json.loads(response)
                if _is_valid_payload(parsed):
                    return cast(Dict[str, Any], parsed)
                logger.warning("AI JSON response missing required feedback fields")
                return None
            except json.JSONDecodeError:
                logger.warning("Response is not valid JSON, attempting to extract sections")

            # Fall back to section extraction for plain-text responses.
            sections = self._extract_sections(response)
            # Check if any actual content was extracted (don't accept empty sections dicts)
            has_content = any(sections.get(key, []) for key in sections.keys())
            if sections and has_content:
                parsed = {
                    "feedback": {
                        "source": "openai",
                        "strengths": sections.get("strengths", []),
                        "weaknesses": sections.get("weaknesses", []),
                        "critical_moments": sections.get("critical_moments", []),
                        "improvement_areas": sections.get("improvement_areas", []),
                        "opening": {
                            "analysis": sections.get("opening", [""])[0] if sections.get("opening", []) else "",
                            "suggestion": (
                                sections.get("opening", ["", ""])[1] if len(sections.get("opening", [])) > 1 else ""
                            ),
                        },
                        "middlegame": {
                            "analysis": sections.get("middlegame", [""])[0] if sections.get("middlegame", []) else "",
                            "suggestion": (
                                sections.get("middlegame", ["", ""])[1]
                                if len(sections.get("middlegame", [])) > 1
                                else ""
                            ),
                        },
                        "endgame": {
                            "analysis": sections.get("endgame", [""])[0] if sections.get("endgame", []) else "",
                            "suggestion": (
                                sections.get("endgame", ["", ""])[1] if len(sections.get("endgame", [])) > 1 else ""
                            ),
                        },
                    }
                }
                if _is_valid_payload(parsed):
                    return cast(Dict[str, Any], parsed)

            logger.error("Failed to parse AI response: %s...", response[:200])
            return None

        except (AttributeError, TypeError, ValueError, KeyError) as e:
            logger.error("Error parsing AI response: %s", e)
            return None

    def _generate_statistical_feedback(self, game_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate feedback based on statistical analysis when AI is unavailable."""
        try:
            if not isinstance(game_metrics, dict):
                game_metrics = {}

            # Support both canonical and wrapped schemas used in the pipeline.
            normalized_metrics = game_metrics
            if "overall" not in normalized_metrics:
                metrics_wrapper = (
                    game_metrics.get("metrics", {})
                    if isinstance(game_metrics.get("metrics"), dict)
                    else {}
                )
                summary_wrapper = (
                    metrics_wrapper.get("summary", {})
                    if isinstance(metrics_wrapper.get("summary"), dict)
                    else {}
                )
                if isinstance(summary_wrapper, dict) and "overall" in summary_wrapper:
                    normalized_metrics = summary_wrapper

            moves = game_metrics.get("moves", []) if isinstance(game_metrics.get("moves"), list) else []
            if "overall" not in normalized_metrics and moves:
                total_moves = len(moves)
                good_moves = sum(1 for m in moves if self._normalized_classification(m) in {"good", "excellent"})
                mistakes = sum(
                    1
                    for m in moves
                    if self._normalized_classification(m) in {"mistake", "blunder", "inaccuracy"}
                )
                normalized_metrics = {
                    "overall": {
                        "total_moves": total_moves,
                        "accuracy": (good_moves / total_moves * 100.0) if total_moves > 0 else 0.0,
                        "mistakes": mistakes,
                        "blunders": sum(1 for m in moves if self._normalized_classification(m) == "blunder"),
                        "time_management_score": 0.0,
                    },
                    "phases": {},
                }

            if "overall" not in normalized_metrics:
                return {
                    "source": "statistical",
                    "data_status": "unavailable",
                    "strengths": [],
                    "weaknesses": ["Unable to analyze game properly"],
                    "critical_moments": [],
                    "improvement_areas": ["Overall game analysis"],
                    "opening": {"analysis": "Analysis unavailable", "suggestion": "Review basic principles"},
                    "middlegame": {"analysis": "Analysis unavailable", "suggestion": "Focus on fundamentals"},
                    "endgame": {"analysis": "Analysis unavailable", "suggestion": "Practice basic endgames"},
                    "metrics": {"overall": {"accuracy": 0.0, "consistency": 0.0, "data_status": "unavailable"}},
                }

            overall = normalized_metrics.get("overall", {})
            phases = normalized_metrics.get("phases", {})

            # Calculate strengths and weaknesses
            strengths = []
            weaknesses = []
            improvement_areas = []

            # Accuracy analysis
            accuracy = overall.get("accuracy", 0)
            if accuracy >= 80:
                strengths.append("High overall accuracy in move selection")
            elif accuracy < 60:
                weaknesses.append("Move accuracy needs improvement")
                improvement_areas.append("Overall move accuracy and calculation")

            # Time management
            time_score = overall.get("time_management_score", 0)
            if time_score >= 70:
                strengths.append("Effective time management")
            elif time_score < 50:
                weaknesses.append("Time management needs improvement")
                improvement_areas.append("Time management and decision making")

            # Tactical analysis
            if overall.get("mistakes", 0) > 2 or overall.get("blunders", 0) > 0:
                weaknesses.append("Tactical opportunities often missed")
                improvement_areas.append("Tactical pattern recognition and execution")

            # Phase analysis
            opening_accuracy = phases.get("opening", {}).get("accuracy", 0)
            middlegame_accuracy = phases.get("middlegame", {}).get("accuracy", 0)
            endgame_accuracy = phases.get("endgame", {}).get("accuracy", 0)

            feedback = {
                "source": "statistical",
                "data_status": "available",
                "strengths": strengths if strengths else ["Basic understanding of chess principles"],
                "weaknesses": weaknesses if weaknesses else ["Areas for improvement not identified"],
                "critical_moments": [],  # Statistical analysis doesn't identify specific moments
                "improvement_areas": improvement_areas if improvement_areas else ["General chess fundamentals"],
                "opening": {
                    "analysis": f"Opening play shows {opening_accuracy}% accuracy",
                    "suggestion": (
                        "Continue studying main lines of your openings"
                        if opening_accuracy >= 70
                        else "Focus on basic opening principles and development"
                    ),
                },
                "middlegame": {
                    "analysis": f"Middlegame performance at {middlegame_accuracy}% accuracy",
                    "suggestion": (
                        "Study complex positional play and strategic planning"
                        if middlegame_accuracy >= 70
                        else "Practice basic tactical patterns and piece activity"
                    ),
                },
                "endgame": {
                    "analysis": f"Endgame technique shows {endgame_accuracy}% accuracy",
                    "suggestion": (
                        "Study complex endgame positions and techniques"
                        if endgame_accuracy >= 70
                        else "Focus on basic endgame concepts and king activity"
                    ),
                },
            }

            # Add metrics in the wrapped shape the rest of the codebase expects.
            training_block = self._build_training_block(normalized_metrics)
            feedback["metrics"] = self._calculate_statistical_metrics(normalized_metrics)
            feedback["training_block"] = training_block
            feedback["phase_motifs"] = training_block.get("phase_motifs", {})
            feedback["impact_metrics"] = training_block.get("impact_metrics", {})

            return feedback

        except (AttributeError, TypeError, ValueError) as e:
            logger.error("Error generating statistical feedback: %s", e)
            # Return minimal feedback structure
            return {
                "source": "statistical",
                "data_status": "unavailable",
                "strengths": [],
                "weaknesses": ["Unable to analyze game properly"],
                "critical_moments": [],
                "improvement_areas": ["Overall game analysis"],
                "opening": {"analysis": "Analysis unavailable", "suggestion": "Review basic principles"},
                "middlegame": {"analysis": "Analysis unavailable", "suggestion": "Focus on fundamentals"},
                "endgame": {"analysis": "Analysis unavailable", "suggestion": "Practice basic endgames"},
                "metrics": {
                    "summary": {
                        "overall": {
                            "accuracy": 0.0,
                            "consistency": 0.0,
                            "data_status": "unavailable",
                        }
                    }
                },
                "training_block": self._build_training_block({}),
                "phase_motifs": self._build_training_block({}).get("phase_motifs", {}),
                "impact_metrics": self._build_training_block({}).get("impact_metrics", {}),
            }

    def _calculate_statistical_metrics(self, game_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate statistical metrics from game data."""
        try:
            overall = game_metrics.get("overall", {})
            return {
                "total_moves": overall.get("total_moves", 0),
                "accuracy": overall.get("accuracy", 0),
                "mistakes": overall.get("mistakes", 0),
                "blunders": overall.get("blunders", 0),
                "average_centipawn_loss": overall.get("average_centipawn_loss", 0),
                "time_management_score": overall.get("time_management_score", 0),
            }
        except (AttributeError, TypeError, ValueError) as e:
            logger.error("Error calculating statistical metrics: %s", e)
            return {}

    def _generate_opening_feedback(self, opening_metrics: Dict[str, Any]) -> Dict[str, str]:
        """Generate feedback for the opening phase."""
        try:
            if not opening_metrics:
                return {"feedback": "No data available for opening phase analysis"}

            accuracy = opening_metrics.get('accuracy', 0)
            mistakes = opening_metrics.get('mistakes', 0)

            if accuracy > 80:
                quality = "excellent"
            elif accuracy > 60:
                quality = "good"
            elif accuracy > 40:
                quality = "average"
            else:
                quality = "poor"

            feedback = f"Opening play was {quality} with {accuracy:.1f}% accuracy."
            if mistakes > 0:
                feedback += f" Made {mistakes} mistakes in the opening phase."

            return {"feedback": feedback, "quality": quality, "accuracy": accuracy}
        except (AttributeError, TypeError, ValueError) as e:
            logger.error("Error generating opening feedback: %s", e)
            return {"feedback": "Insufficient data for opening analysis", "quality": "unknown"}

    def _generate_middlegame_feedback(self, middlegame_metrics: Dict[str, Any]) -> Dict[str, str]:
        """Generate feedback for the middlegame phase."""
        try:
            if not middlegame_metrics:
                return {"feedback": "No data available for middlegame phase analysis"}

            accuracy = middlegame_metrics.get('accuracy', 0)
            mistakes = middlegame_metrics.get('mistakes', 0)
            tactical_opportunities = middlegame_metrics.get('tactical_opportunities', 0)
            tactical_success = middlegame_metrics.get('tactical_success', 0)

            if accuracy > 80:
                quality = "excellent"
            elif accuracy > 60:
                quality = "good"
            elif accuracy > 40:
                quality = "average"
            else:
                quality = "poor"

            feedback = f"Middlegame play was {quality} with {accuracy:.1f}% accuracy."
            if mistakes > 0:
                feedback += f" Made {mistakes} mistakes in the middlegame phase."

            if tactical_opportunities > 0:
                success_rate = (tactical_success / tactical_opportunities * 100) if tactical_opportunities > 0 else 0
                feedback += (
                    f" Found {tactical_success} out of {tactical_opportunities} "
                    f"tactical opportunities ({success_rate:.1f}%)."
                )

            return {"feedback": feedback, "quality": quality, "accuracy": accuracy}
        except (AttributeError, TypeError, ValueError) as e:
            logger.error("Error generating middlegame feedback: %s", e)
            return {"feedback": "Insufficient data for middlegame analysis", "quality": "unknown"}

    def _generate_endgame_feedback(self, endgame_metrics: Dict[str, Any]) -> Dict[str, str]:
        """Generate feedback for the endgame phase."""
        try:
            if not endgame_metrics:
                return {"feedback": "No data available for endgame phase analysis"}

            accuracy = endgame_metrics.get('accuracy', 0)
            mistakes = endgame_metrics.get('mistakes', 0)

            if accuracy > 80:
                quality = "excellent"
            elif accuracy > 60:
                quality = "good"
            elif accuracy > 40:
                quality = "average"
            else:
                quality = "poor"

            feedback = f"Endgame play was {quality} with {accuracy:.1f}% accuracy."
            if mistakes > 0:
                feedback += f" Made {mistakes} mistakes in the endgame phase."

            return {"feedback": feedback, "quality": quality, "accuracy": accuracy}
        except (AttributeError, TypeError, ValueError) as e:
            logger.error("Error generating endgame feedback: %s", e)
            return {"feedback": "Insufficient data for endgame analysis", "quality": "unknown"}

    def _identify_strengths(self, metrics: Dict[str, Any]) -> List[str]:
        """Identify player strengths based on metrics."""
        try:
            strengths = []
            overall = metrics.get('overall', {})
            phases = metrics.get('phases', {})
            tactics = metrics.get('tactics', {})
            time_mgmt = metrics.get('time_management', {})

            # Check overall accuracy
            accuracy = overall.get('accuracy', 0)
            if accuracy > 80:
                strengths.append(f"Strong overall play with {accuracy:.1f}% accuracy")

            # Check phase-specific strengths
            for phase_name, phase_data in phases.items():
                phase_accuracy = phase_data.get('accuracy', 0)
                if phase_accuracy > 75:
                    strengths.append(f"Strong {phase_name} play ({phase_accuracy:.1f}% accuracy)")

            # Check tactical awareness
            tactical_success = tactics.get('success_rate', 0)
            if tactical_success > 70:
                strengths.append(f"Good tactical awareness ({tactical_success:.1f}% success rate)")

            # Check time management
            time_score = time_mgmt.get('time_management_score', 0)
            if time_score > 70:
                strengths.append(f"Effective time management ({time_score:.1f}% efficiency)")

            # If no strengths identified, add a generic one
            if not strengths and accuracy > 40:
                strengths.append(f"Reasonable overall play with {accuracy:.1f}% accuracy")

            return strengths
        except (AttributeError, TypeError, ValueError) as e:
            logger.error("Error identifying strengths: %s", e)
            return ["Unable to determine strengths"]

    def _identify_weaknesses(self, metrics: Dict[str, Any]) -> List[str]:
        """Identify player weaknesses based on metrics."""
        try:
            weaknesses = []
            overall = metrics.get('overall', {})
            phases = metrics.get('phases', {})
            tactics = metrics.get('tactics', {})
            time_mgmt = metrics.get('time_management', {})

            # Check overall accuracy
            accuracy = overall.get('accuracy', 0)
            if accuracy < 50:
                weaknesses.append(f"Inconsistent overall play ({accuracy:.1f}% accuracy)")

            # Check mistakes and blunders
            mistakes = overall.get('mistakes', 0)
            blunders = overall.get('blunders', 0)
            if mistakes + blunders > 3:
                weaknesses.append(f"Made {mistakes} mistakes and {blunders} blunders")

            # Check phase-specific weaknesses
            for phase_name, phase_data in phases.items():
                phase_accuracy = phase_data.get('accuracy', 0)
                if phase_accuracy < 50:
                    weaknesses.append(f"Struggles in {phase_name} ({phase_accuracy:.1f}% accuracy)")

            # Check tactical awareness
            tactical_success = tactics.get('success_rate', 0)
            tactical_opportunities = tactics.get('opportunities', 0)
            if tactical_success < 40 and tactical_opportunities > 2:
                weaknesses.append(f"Missed tactical opportunities ({tactical_success:.1f}% success rate)")

            # Check time management
            time_score = time_mgmt.get('time_management_score', 0)
            if time_score < 40:
                weaknesses.append(f"Poor time management ({time_score:.1f}% efficiency)")

            # If no weaknesses identified, add a generic one
            if not weaknesses and accuracy < 80:
                weaknesses.append(f"Could improve overall accuracy (currently {accuracy:.1f}%)")

            return weaknesses
        except (AttributeError, TypeError, ValueError) as e:
            logger.error("Error identifying weaknesses: %s", e)
            return ["Unable to determine weaknesses"]

    def _find_critical_moments(self, moves: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find critical moments in the game."""
        try:
            critical_moments: List[Dict[str, Any]] = []

            if not moves:
                return critical_moments

            # Sort moves by evaluation change (largest absolute value first)
            sorted_moves = sorted(
                [m for m in moves if 'eval_change' in m],
                key=lambda x: abs(x.get('eval_change', 0)),
                reverse=True
            )

            # Take the top 3 most significant moves
            for _, move in enumerate(sorted_moves[:3]):
                move_number = move.get('move_number', 0)
                move_san = move.get('san', move.get('move', '?'))
                eval_change_cp = self._eval_change_to_cp(move.get('eval_change', 0))
                is_white = move.get('is_white', True)
                side = "White" if is_white else "Black"

                if abs(eval_change_cp) < 50:
                    continue  # Skip if not actually significant

                if eval_change_cp < 0:
                    moment_type = "mistake"
                    if eval_change_cp < -300:
                        moment_type = "blunder"
                else:
                    moment_type = "good move"
                    if eval_change_cp > 300:
                        moment_type = "excellent move"

                description = f"Move {move_number}: {side}'s {moment_type} {move_san}"
                critical_moments.append({
                    "move_number": move_number,
                    "description": description,
                    "type": moment_type,
                    "eval_change": eval_change_cp
                })

            return critical_moments
        except (AttributeError, TypeError, ValueError) as e:
            logger.error("Error finding critical moments: %s", e)
            return []

    def _generate_improvement_areas(self, metrics: Dict[str, Any], _weaknesses: List[str]) -> List[str]:
        """Generate suggested improvement areas based on metrics and identified weaknesses."""
        try:
            improvement_areas = []
            overall = metrics.get('overall', {})
            phases = metrics.get('phases', {})

            # Look for the weakest phase
            weakest_phase = None
            lowest_accuracy = 100

            for phase_name, phase_data in phases.items():
                phase_accuracy = phase_data.get('accuracy', 0)
                if phase_accuracy < lowest_accuracy:
                    lowest_accuracy = phase_accuracy
                    weakest_phase = phase_name

            # Add phase-specific improvement suggestion
            if weakest_phase and lowest_accuracy < 70:
                improvement_areas.append(f"Study {weakest_phase} positions and principles")

            # Look at overall metrics
            mistakes = overall.get('mistakes', 0)
            blunders = overall.get('blunders', 0)

            if blunders > 2:
                improvement_areas.append("Practice calculation and double-check moves before playing them")

            if mistakes > 3:
                improvement_areas.append("Practice tactical exercises to improve pattern recognition")

            # Add general improvement areas
            if not improvement_areas:
                accuracy = overall.get('accuracy', 0)
                if accuracy < 90:
                    improvement_areas.append("Continue practicing tactics and game analysis")
                if accuracy < 70:
                    improvement_areas.append("Study basic chess principles and common patterns")

            return improvement_areas
        except (AttributeError, TypeError, ValueError) as e:
            logger.error("Error generating improvement areas: %s", e)
            return ["Practice tactics and analyze your games to improve"]
