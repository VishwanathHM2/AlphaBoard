"""
move.py - Move representation for the chess engine.

A Move stores the from-square, to-square, and optional metadata
(promotion piece, en-passant capture, castling).  It is intentionally
a lightweight data container with no board knowledge.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Move:
    """
    Represents a single chess move.

    Attributes
    ----------
    from_sq : int
        Source square index (0-63).
    to_sq : int
        Destination square index (0-63).
    promotion : str or None
        Piece character to promote to ('Q','R','B','N' uppercase).
        None when not a promotion.
    is_en_passant : bool
        True when this move captures via en passant.
    is_castling : bool
        True when this move is a king castling move.
    captured_piece : str or None
        Piece character that was on to_sq (filled in by make_move).
    """

    from_sq: int
    to_sq: int
    promotion: Optional[str] = None
    is_en_passant: bool = False
    is_castling: bool = False
    # Filled in during make_move; useful for undo_move
    captured_piece: Optional[str] = field(default=None, repr=False)

    # ──────────────────────────────────────────
    # Algebraic helpers
    # ──────────────────────────────────────────

    @staticmethod
    def _sq_to_alg(sq: int) -> str:
        """Convert board index → algebraic square string (e.g. 28 → 'e4')."""
        file_char = chr(ord("a") + sq % 8)
        rank_char = str(sq // 8 + 1)
        return file_char + rank_char

    def to_uci(self) -> str:
        """Return move in UCI long-algebraic format (e.g. 'e2e4', 'e7e8q')."""
        base = self._sq_to_alg(self.from_sq) + self._sq_to_alg(self.to_sq)
        if self.promotion:
            base += self.promotion.lower()
        return base

    def __str__(self) -> str:
        return self.to_uci()

    def __repr__(self) -> str:
        extras = []
        if self.promotion:
            extras.append(f"promo={self.promotion}")
        if self.is_en_passant:
            extras.append("ep")
        if self.is_castling:
            extras.append("castling")
        suffix = f"({', '.join(extras)})" if extras else ""
        return f"Move({self.to_uci()}{suffix})"
