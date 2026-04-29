"""
Unit tests for explanation_templates module.

Tests the template-based move explanation generator against all five tactical themes.
Each test verifies that the generated explanation:
1. Includes the played move
2. Includes the best move
3. Includes theme-specific context from the context dict
4. Is a non-empty string
"""

import pytest
from core.analysis.explanation_templates import get_explanation


class TestExplanationTemplates:
    """Test suite for tactical theme explanation generation."""

    def test_hanging_piece_explanation(self):
        """Test explanation for hanging_piece (undefended piece loss)."""
        context = {
            "attacking_piece_name": "Black rook",
            "lost_piece_name": "your knight",
        }

        explanation = get_explanation(
            tactical_theme="hanging_piece",
            played_move="Nxd5",
            best_move="Qd1",
            context=context,
        )

        # Verify explanation contains key elements
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "Nxd5" in explanation  # Played move
        assert "Qd1" in explanation  # Best move
        assert "undefended" in explanation.lower()  # Theme-specific
        assert "your knight" in explanation  # Context-specific

    def test_fork_explanation(self):
        """Test explanation for fork (attacking multiple pieces)."""
        context = {
            "your_piece_name": "your bishop",
            "targeted_pieces": "the rook and queen",
        }

        explanation = get_explanation(
            tactical_theme="fork",
            played_move="Be4",
            best_move="Nf6",
            context=context,
        )

        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "Be4" in explanation  # Played move
        assert "Nf6" in explanation  # Best move
        assert "fork" in explanation.lower()  # Theme-specific
        assert "the rook and queen" in explanation  # Context-specific

    def test_pin_explanation(self):
        """Test explanation for pin (piece cannot move without exposing more valuable piece)."""
        context = {
            "pinned_piece_name": "your rook",
            "valuable_piece_name": "your king",
            "pin_direction": "file",
        }

        explanation = get_explanation(
            tactical_theme="pin",
            played_move="Rc5",
            best_move="Kg2",
            context=context,
        )

        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "Rc5" in explanation  # Played move
        assert "Kg2" in explanation  # Best move
        assert "pin" in explanation.lower()  # Theme-specific
        assert "your rook" in explanation  # Context-specific
        assert "file" in explanation  # Pin direction

    def test_skewer_explanation(self):
        """Test explanation for skewer (valuable piece forced to move, less valuable exposed)."""
        context = {
            "valuable_piece_name": "your queen",
            "less_valuable_piece_name": "your rook",
        }

        explanation = get_explanation(
            tactical_theme="skewer",
            played_move="Be2",
            best_move="Qe7",
            context=context,
        )

        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "Be2" in explanation  # Played move
        assert "Qe7" in explanation  # Best move
        assert "skewer" in explanation.lower()  # Theme-specific
        assert "your queen" in explanation  # Context-specific
        assert "your rook" in explanation  # Less valuable piece

    def test_missed_tactic_fallback(self):
        """Test fallback explanation for unclassified tactical themes."""
        context = {
            "eval_difference": "nearly a pawn",
        }

        explanation = get_explanation(
            tactical_theme="missed_tactic",
            played_move="h4",
            best_move="Bf4",
            context=context,
        )

        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "h4" in explanation  # Played move
        assert "Bf4" in explanation  # Best move
        assert "deteriorated" in explanation or "weaker" in explanation.lower()

    def test_unrecognized_theme_uses_fallback(self):
        """Test that unrecognized tactical themes use the missed_tactic fallback."""
        context = {"eval_difference": "0.5 pawns"}

        explanation = get_explanation(
            tactical_theme="unknown_theme_xyz",
            played_move="a3",
            best_move="a4",
            context=context,
        )

        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "a3" in explanation  # Played move
        assert "a4" in explanation  # Best move
        # Should use fallback language
        assert "deteriorated" in explanation or "weaker" in explanation.lower()

    def test_empty_context_dict(self):
        """Test that explanations work with empty context dict (graceful degradation)."""
        explanation = get_explanation(
            tactical_theme="fork",
            played_move="Nc3",
            best_move="Nd5",
            context={},
        )

        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "Nc3" in explanation
        assert "Nd5" in explanation
        # Should still mention "fork"
        assert "fork" in explanation.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
