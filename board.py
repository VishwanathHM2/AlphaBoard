"""
board.py - Chess board representation and move execution.

The board is a flat list of 64 squares (index 0 = a1, index 63 = h8).
Uppercase letters are White pieces; lowercase are Black; '.' is empty.

State tracked:
  - squares[]     : 64-element list of piece characters
  - side_to_move  : 'white' or 'black'
  - castling      : bitmask (CASTLE_WK | CASTLE_WQ | CASTLE_BK | CASTLE_BQ)
  - en_passant    : board index of en-passant target square, or None
  - halfmove_clock: moves since last capture or pawn push
  - fullmove      : starts at 1, incremented after Black moves

Square indexing (matches rank-1-first, file-a-first):
  index = rank * 8 + file   (rank 0 = rank-1, file 0 = file-a)
  a1=0, b1=1, ..., h1=7, a2=8, ..., h8=63
"""

from __future__ import annotations
from typing import List, Optional
from copy import deepcopy

from constants import (
    WHITE, BLACK, EMPTY, WHITE_PIECES, BLACK_PIECES,
    CASTLE_WK, CASTLE_WQ, CASTLE_BK, CASTLE_BQ,
    sq, rank_of, file_of,
)
from move import Move


# ──────────────────────────────────────────────────────────────────────────────
# FEN parsing helpers
# ──────────────────────────────────────────────────────────────────────────────

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def _alg_to_sq(alg: str) -> int:
    """Convert algebraic square (e.g. 'e4') to board index."""
    return (int(alg[1]) - 1) * 8 + (ord(alg[0]) - ord("a"))


class Board:
    """
    Represents the full chess game state.

    Attributes
    ----------
    squares : list[str]
        64-element list of piece characters / '.'.
    side_to_move : str
        'white' or 'black'.
    castling : int
        Bitmask of remaining castling rights.
    en_passant : int or None
        Target square for en passant, or None.
    halfmove_clock : int
        Fifty-move rule counter.
    fullmove : int
        Full-move counter.
    """

    __slots__ = (
        "squares", "side_to_move", "castling",
        "en_passant", "halfmove_clock", "fullmove",
    )

    def __init__(self) -> None:
        self.squares: List[str] = [EMPTY] * 64
        self.side_to_move: str = WHITE
        self.castling: int = 0
        self.en_passant: Optional[int] = None
        self.halfmove_clock: int = 0
        self.fullmove: int = 1

    # ──────────────────────────────────────────
    # FEN I/O
    # ──────────────────────────────────────────

    @classmethod
    def from_fen(cls, fen: str) -> "Board":
        """
        Parse a FEN string and return a Board.

        FEN field order: <pieces> <side> <castling> <ep> <half> <full>
        """
        board = cls()
        parts = fen.split()
        piece_str, side, cast_str, ep_str = parts[0], parts[1], parts[2], parts[3]
        half = int(parts[4]) if len(parts) > 4 else 0
        full = int(parts[5]) if len(parts) > 5 else 1

        # Pieces – FEN ranks go rank-8 first
        ranks = piece_str.split("/")
        for rank_idx, rank_fen in enumerate(reversed(ranks)):
            file_idx = 0
            for ch in rank_fen:
                if ch.isdigit():
                    file_idx += int(ch)
                else:
                    board.squares[rank_idx * 8 + file_idx] = ch
                    file_idx += 1

        board.side_to_move = WHITE if side == "w" else BLACK
        board.castling = 0
        if "K" in cast_str: board.castling |= CASTLE_WK
        if "Q" in cast_str: board.castling |= CASTLE_WQ
        if "k" in cast_str: board.castling |= CASTLE_BK
        if "q" in cast_str: board.castling |= CASTLE_BQ

        board.en_passant = _alg_to_sq(ep_str) if ep_str != "-" else None
        board.halfmove_clock = half
        board.fullmove = full
        return board

    def to_fen(self) -> str:
        """Serialize board state back to a FEN string."""
        rows = []
        for rank in range(7, -1, -1):
            row = ""
            empty_count = 0
            for file in range(8):
                pc = self.squares[rank * 8 + file]
                if pc == EMPTY:
                    empty_count += 1
                else:
                    if empty_count:
                        row += str(empty_count)
                        empty_count = 0
                    row += pc
            if empty_count:
                row += str(empty_count)
            rows.append(row)

        piece_str = "/".join(rows)
        side = "w" if self.side_to_move == WHITE else "b"
        cast = ""
        if self.castling & CASTLE_WK: cast += "K"
        if self.castling & CASTLE_WQ: cast += "Q"
        if self.castling & CASTLE_BK: cast += "k"
        if self.castling & CASTLE_BQ: cast += "q"
        if not cast: cast = "-"
        ep = "-" if self.en_passant is None else (
            chr(ord("a") + self.en_passant % 8) + str(self.en_passant // 8 + 1)
        )
        return f"{piece_str} {side} {cast} {ep} {self.halfmove_clock} {self.fullmove}"

    # ──────────────────────────────────────────
    # Display
    # ──────────────────────────────────────────

    def display(self) -> str:
        """Return a Unicode-friendly ASCII board string."""
        lines = ["  +------------------------+"]
        for rank in range(7, -1, -1):
            row_pieces = " ".join(self.squares[rank * 8 + f] for f in range(8))
            lines.append(f"{rank + 1} | {row_pieces} |")
        lines.append("  +------------------------+")
        lines.append("    a b c d e f g h")
        side = "White" if self.side_to_move == WHITE else "Black"
        lines.append(f"  Side to move: {side}  Move: {self.fullmove}")
        return "\n".join(lines)

    # ──────────────────────────────────────────
    # Make / Undo move
    # ──────────────────────────────────────────

    def make_move(self, move: Move) -> "_UndoInfo":
        """
        Apply *move* to the board in-place.

        Returns an _UndoInfo object that can be passed to undo_move()
        to fully restore the previous state.
        """
        undo = _UndoInfo(
            castling=self.castling,
            en_passant=self.en_passant,
            halfmove_clock=self.halfmove_clock,
            captured_piece=self.squares[move.to_sq],
        )

        piece = self.squares[move.from_sq]

        # ── Update halfmove clock ──
        if piece.upper() == "P" or self.squares[move.to_sq] != EMPTY:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        # ── En passant capture ──
        if move.is_en_passant:
            # Remove the captured pawn (it's not on to_sq)
            if self.side_to_move == WHITE:
                captured_pawn_sq = move.to_sq - 8   # pawn one rank below
            else:
                captured_pawn_sq = move.to_sq + 8
            undo.ep_capture_sq = captured_pawn_sq
            undo.ep_captured_piece = self.squares[captured_pawn_sq]
            self.squares[captured_pawn_sq] = EMPTY

        # ── Castling: also move the rook ──
        if move.is_castling:
            if move.to_sq == sq(6, 0):      # White kingside (g1)
                self.squares[sq(5, 0)] = "R"
                self.squares[sq(7, 0)] = EMPTY
            elif move.to_sq == sq(2, 0):    # White queenside (c1)
                self.squares[sq(3, 0)] = "R"
                self.squares[sq(0, 0)] = EMPTY
            elif move.to_sq == sq(6, 7):    # Black kingside (g8)
                self.squares[sq(5, 7)] = "r"
                self.squares[sq(7, 7)] = EMPTY
            elif move.to_sq == sq(2, 7):    # Black queenside (c8)
                self.squares[sq(3, 7)] = "r"
                self.squares[sq(0, 7)] = EMPTY

        # ── Move the piece ──
        dest_piece = move.promotion if move.promotion else piece
        # Promote: White promotes to uppercase, Black to lowercase
        if move.promotion:
            dest_piece = move.promotion if self.side_to_move == WHITE else move.promotion.lower()
        self.squares[move.to_sq] = dest_piece
        self.squares[move.from_sq] = EMPTY

        # ── Update en passant target ──
        self.en_passant = None
        if piece.upper() == "P":
            from_rank = rank_of(move.from_sq)
            to_rank = rank_of(move.to_sq)
            if abs(to_rank - from_rank) == 2:
                # Double pawn push → set ep target square
                ep_rank = (from_rank + to_rank) // 2
                self.en_passant = sq(file_of(move.from_sq), ep_rank)

        # ── Update castling rights ──
        self._update_castling_rights(move.from_sq, move.to_sq)

        # ── Flip side to move ──
        if self.side_to_move == BLACK:
            self.fullmove += 1
        self.side_to_move = BLACK if self.side_to_move == WHITE else WHITE

        return undo

    def undo_move(self, move: Move, undo: "_UndoInfo") -> None:
        """
        Restore board state after make_move().

        Parameters
        ----------
        move : Move
            The move that was applied.
        undo : _UndoInfo
            Object returned by make_move().
        """
        # Flip side back
        self.side_to_move = BLACK if self.side_to_move == WHITE else WHITE
        if self.side_to_move == BLACK:
            self.fullmove -= 1

        # Restore moved piece (undo promotion)
        moved_piece = self.squares[move.to_sq]
        if move.promotion:
            moved_piece = "P" if self.side_to_move == WHITE else "p"
        self.squares[move.from_sq] = moved_piece
        self.squares[move.to_sq] = undo.captured_piece

        # Restore en-passant captured pawn
        if move.is_en_passant and undo.ep_capture_sq is not None:
            self.squares[undo.ep_capture_sq] = undo.ep_captured_piece

        # Restore castling rook
        if move.is_castling:
            if move.to_sq == sq(6, 0):
                self.squares[sq(7, 0)] = "R"
                self.squares[sq(5, 0)] = EMPTY
            elif move.to_sq == sq(2, 0):
                self.squares[sq(0, 0)] = "R"
                self.squares[sq(3, 0)] = EMPTY
            elif move.to_sq == sq(6, 7):
                self.squares[sq(7, 7)] = "r"
                self.squares[sq(5, 7)] = EMPTY
            elif move.to_sq == sq(2, 7):
                self.squares[sq(0, 7)] = "r"
                self.squares[sq(3, 7)] = EMPTY

        # Restore state variables
        self.castling = undo.castling
        self.en_passant = undo.en_passant
        self.halfmove_clock = undo.halfmove_clock

    # ──────────────────────────────────────────
    # Castling rights helper
    # ──────────────────────────────────────────

    def _update_castling_rights(self, from_sq: int, to_sq: int) -> None:
        """Revoke castling rights when a king or rook moves/is captured."""
        # King moves
        if from_sq == sq(4, 0):  # e1
            self.castling &= ~(CASTLE_WK | CASTLE_WQ)
        elif from_sq == sq(4, 7):  # e8
            self.castling &= ~(CASTLE_BK | CASTLE_BQ)
        # Rook moves (or captured)
        if from_sq == sq(7, 0) or to_sq == sq(7, 0):
            self.castling &= ~CASTLE_WK
        if from_sq == sq(0, 0) or to_sq == sq(0, 0):
            self.castling &= ~CASTLE_WQ
        if from_sq == sq(7, 7) or to_sq == sq(7, 7):
            self.castling &= ~CASTLE_BK
        if from_sq == sq(0, 7) or to_sq == sq(0, 7):
            self.castling &= ~CASTLE_BQ

    # ──────────────────────────────────────────
    # Convenience queries
    # ──────────────────────────────────────────

    def piece_at(self, index: int) -> str:
        return self.squares[index]

    def is_empty(self, index: int) -> bool:
        return self.squares[index] == EMPTY

    def is_white_piece(self, index: int) -> bool:
        return self.squares[index] in WHITE_PIECES

    def is_black_piece(self, index: int) -> bool:
        return self.squares[index] in BLACK_PIECES

    def friendly_piece(self, index: int) -> bool:
        """Return True if the square has a friendly (current side) piece."""
        if self.side_to_move == WHITE:
            return self.is_white_piece(index)
        return self.is_black_piece(index)

    def enemy_piece(self, index: int) -> bool:
        """Return True if the square has an enemy piece."""
        if self.side_to_move == WHITE:
            return self.is_black_piece(index)
        return self.is_white_piece(index)

    def find_king(self, side: str) -> int:
        """Return the board index of the king for *side*."""
        king = "K" if side == WHITE else "k"
        return self.squares.index(king)

    def copy(self) -> "Board":
        """Return a deep copy of the board."""
        b = Board()
        b.squares = self.squares[:]
        b.side_to_move = self.side_to_move
        b.castling = self.castling
        b.en_passant = self.en_passant
        b.halfmove_clock = self.halfmove_clock
        b.fullmove = self.fullmove
        return b


# ──────────────────────────────────────────────────────────────────────────────
# Internal undo record
# ──────────────────────────────────────────────────────────────────────────────

class _UndoInfo:
    """
    Snapshot of the board state fields that change during a move.
    Stored on the call stack so we can restore the board without copying.
    """
    __slots__ = (
        "castling", "en_passant", "halfmove_clock",
        "captured_piece", "ep_capture_sq", "ep_captured_piece",
    )

    def __init__(self, castling, en_passant, halfmove_clock, captured_piece):
        self.castling = castling
        self.en_passant = en_passant
        self.halfmove_clock = halfmove_clock
        self.captured_piece = captured_piece
        self.ep_capture_sq: Optional[int] = None
        self.ep_captured_piece: str = EMPTY
