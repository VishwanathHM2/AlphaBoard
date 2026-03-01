"""
move_generator.py - Legal move generation for all piece types.

Strategy
--------
1. Generate *pseudo-legal* moves for every piece of the current side.
2. Filter: keep only moves that do not leave our king in check.

This two-step approach is simpler and correct, though slightly slower
than generating only legal moves directly.  For a Level-2 engine the
performance is entirely acceptable.

Attack map
----------
is_square_attacked(board, sq, by_side) is the key helper used for:
  - Check detection after make_move
  - Castling legality (king must not pass through attacked squares)
"""

from __future__ import annotations
from typing import List, Optional

from constants import (
    WHITE, BLACK, EMPTY, WHITE_PIECES, BLACK_PIECES,
    CASTLE_WK, CASTLE_WQ, CASTLE_BK, CASTLE_BQ,
    sq, rank_of, file_of,
)
from move import Move
from board import Board


# ──────────────────────────────────────────────────────────────────────────────
# Direction vectors
# ──────────────────────────────────────────────────────────────────────────────

KNIGHT_DELTAS = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                 (1, -2),  (1, 2),  (2, -1),  (2, 1)]

BISHOP_DIRS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
ROOK_DIRS   = [(-1, 0),  (1, 0),  (0, -1), (0, 1)]
QUEEN_DIRS  = BISHOP_DIRS + ROOK_DIRS
KING_DIRS   = QUEEN_DIRS


def _sq_from_delta(index: int, df: int, dr: int) -> Optional[int]:
    """
    Return the board index reached from *index* by (df, dr) delta,
    or None if it would fall off the board.
    """
    f = file_of(index) + df
    r = rank_of(index) + dr
    if 0 <= f < 8 and 0 <= r < 8:
        return r * 8 + f
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Attack detection
# ──────────────────────────────────────────────────────────────────────────────

def is_square_attacked(board: Board, target: int, by_side: str) -> bool:
    """
    Return True if *target* square is attacked by *by_side*.

    Checks all attack patterns from the target square outward
    (reverse-ray approach), which is simpler and equally correct.
    """
    # Pawn attacks (reverse: look FROM target where pawns could be)
    pawn_char = "P" if by_side == WHITE else "p"
    pawn_attack_dr = -1 if by_side == WHITE else 1  # rank direction FROM target
    for df in (-1, 1):
        s = _sq_from_delta(target, df, pawn_attack_dr)
        if s is not None and board.squares[s] == pawn_char:
            return True

    # Knight attacks
    knight_char = "N" if by_side == WHITE else "n"
    for df, dr in KNIGHT_DELTAS:
        s = _sq_from_delta(target, df, dr)
        if s is not None and board.squares[s] == knight_char:
            return True

    # Bishop / Queen (diagonal)
    b_chars = {"B", "Q"} if by_side == WHITE else {"b", "q"}
    for df, dr in BISHOP_DIRS:
        s = target
        while True:
            s = _sq_from_delta(s, df, dr)
            if s is None:
                break
            pc = board.squares[s]
            if pc != EMPTY:
                if pc in b_chars:
                    return True
                break

    # Rook / Queen (straight)
    r_chars = {"R", "Q"} if by_side == WHITE else {"r", "q"}
    for df, dr in ROOK_DIRS:
        s = target
        while True:
            s = _sq_from_delta(s, df, dr)
            if s is None:
                break
            pc = board.squares[s]
            if pc != EMPTY:
                if pc in r_chars:
                    return True
                break

    # King (just one step – prevents two kings being adjacent)
    king_char = "K" if by_side == WHITE else "k"
    for df, dr in KING_DIRS:
        s = _sq_from_delta(target, df, dr)
        if s is not None and board.squares[s] == king_char:
            return True

    return False


def is_in_check(board: Board, side: str) -> bool:
    """Return True if *side*'s king is currently in check."""
    king_sq = board.find_king(side)
    opponent = BLACK if side == WHITE else WHITE
    return is_square_attacked(board, king_sq, opponent)


# ──────────────────────────────────────────────────────────────────────────────
# Pseudo-legal move generators (piece-specific)
# ──────────────────────────────────────────────────────────────────────────────

def _gen_pawn_moves(board: Board, from_sq: int) -> List[Move]:
    moves: List[Move] = []
    side = board.side_to_move
    dr = 1 if side == WHITE else -1   # rank direction of advance
    start_rank = 1 if side == WHITE else 6
    promo_rank = 7 if side == WHITE else 0

    # ── Single push ──
    one = _sq_from_delta(from_sq, 0, dr)
    if one is not None and board.is_empty(one):
        if rank_of(one) == promo_rank:
            for p in ("Q", "R", "B", "N"):
                moves.append(Move(from_sq, one, promotion=p))
        else:
            moves.append(Move(from_sq, one))

        # ── Double push from starting rank ──
        if rank_of(from_sq) == start_rank:
            two = _sq_from_delta(one, 0, dr)
            if two is not None and board.is_empty(two):
                moves.append(Move(from_sq, two))

    # ── Diagonal captures ──
    for df in (-1, 1):
        cap = _sq_from_delta(from_sq, df, dr)
        if cap is None:
            continue
        if board.enemy_piece(cap):
            if rank_of(cap) == promo_rank:
                for p in ("Q", "R", "B", "N"):
                    moves.append(Move(from_sq, cap, promotion=p))
            else:
                moves.append(Move(from_sq, cap))
        # ── En passant ──
        elif board.en_passant == cap:
            moves.append(Move(from_sq, cap, is_en_passant=True))

    return moves


def _gen_knight_moves(board: Board, from_sq: int) -> List[Move]:
    moves: List[Move] = []
    for df, dr in KNIGHT_DELTAS:
        to = _sq_from_delta(from_sq, df, dr)
        if to is not None and not board.friendly_piece(to):
            moves.append(Move(from_sq, to))
    return moves


def _gen_sliding_moves(board: Board, from_sq: int, directions) -> List[Move]:
    moves: List[Move] = []
    for df, dr in directions:
        s = from_sq
        while True:
            s = _sq_from_delta(s, df, dr)
            if s is None:
                break
            if board.friendly_piece(s):
                break
            moves.append(Move(from_sq, s))
            if board.enemy_piece(s):
                break   # can capture but not slide through
    return moves


def _gen_king_moves(board: Board, from_sq: int) -> List[Move]:
    moves: List[Move] = []
    for df, dr in KING_DIRS:
        to = _sq_from_delta(from_sq, df, dr)
        if to is not None and not board.friendly_piece(to):
            moves.append(Move(from_sq, to))

    # ── Castling ──
    side = board.side_to_move
    opponent = BLACK if side == WHITE else WHITE

    if not is_square_attacked(board, from_sq, opponent):  # king not in check
        if side == WHITE:
            # Kingside: f1 and g1 must be empty; e1, f1, g1 not attacked
            if (board.castling & CASTLE_WK
                    and board.is_empty(sq(5, 0)) and board.is_empty(sq(6, 0))
                    and not is_square_attacked(board, sq(5, 0), BLACK)
                    and not is_square_attacked(board, sq(6, 0), BLACK)):
                moves.append(Move(from_sq, sq(6, 0), is_castling=True))
            # Queenside: b1, c1, d1 empty; e1, d1, c1 not attacked
            if (board.castling & CASTLE_WQ
                    and board.is_empty(sq(3, 0)) and board.is_empty(sq(2, 0)) and board.is_empty(sq(1, 0))
                    and not is_square_attacked(board, sq(3, 0), BLACK)
                    and not is_square_attacked(board, sq(2, 0), BLACK)):
                moves.append(Move(from_sq, sq(2, 0), is_castling=True))
        else:
            if (board.castling & CASTLE_BK
                    and board.is_empty(sq(5, 7)) and board.is_empty(sq(6, 7))
                    and not is_square_attacked(board, sq(5, 7), WHITE)
                    and not is_square_attacked(board, sq(6, 7), WHITE)):
                moves.append(Move(from_sq, sq(6, 7), is_castling=True))
            if (board.castling & CASTLE_BQ
                    and board.is_empty(sq(3, 7)) and board.is_empty(sq(2, 7)) and board.is_empty(sq(1, 7))
                    and not is_square_attacked(board, sq(3, 7), WHITE)
                    and not is_square_attacked(board, sq(2, 7), WHITE)):
                moves.append(Move(from_sq, sq(2, 7), is_castling=True))

    return moves


# ──────────────────────────────────────────────────────────────────────────────
# Main entry points
# ──────────────────────────────────────────────────────────────────────────────

def generate_pseudo_legal_moves(board: Board) -> List[Move]:
    """
    Generate all pseudo-legal moves for the current side to move.

    Pseudo-legal moves may include positions where the moving side's king
    is in check after the move.  Use generate_legal_moves() for play.
    """
    moves: List[Move] = []
    side = board.side_to_move

    for i in range(64):
        pc = board.squares[i]
        if pc == EMPTY:
            continue
        if side == WHITE and pc not in WHITE_PIECES:
            continue
        if side == BLACK and pc not in BLACK_PIECES:
            continue

        pc_upper = pc.upper()
        if pc_upper == "P":
            moves.extend(_gen_pawn_moves(board, i))
        elif pc_upper == "N":
            moves.extend(_gen_knight_moves(board, i))
        elif pc_upper == "B":
            moves.extend(_gen_sliding_moves(board, i, BISHOP_DIRS))
        elif pc_upper == "R":
            moves.extend(_gen_sliding_moves(board, i, ROOK_DIRS))
        elif pc_upper == "Q":
            moves.extend(_gen_sliding_moves(board, i, QUEEN_DIRS))
        elif pc_upper == "K":
            moves.extend(_gen_king_moves(board, i))

    return moves


def generate_legal_moves(board: Board) -> List[Move]:
    """
    Generate all fully legal moves for the current side to move.

    Filters out pseudo-legal moves that leave the moving side's king
    in check.
    """
    pseudo = generate_pseudo_legal_moves(board)
    legal: List[Move] = []
    side = board.side_to_move

    for move in pseudo:
        undo = board.make_move(move)
        # After the move, check if OUR king is now in check
        if not is_in_check(board, side):
            legal.append(move)
        board.undo_move(move, undo)

    return legal


def generate_capture_moves(board: Board) -> List[Move]:
    """
    Return only legal capture moves (used in quiescence search).

    En passant is included as it is also a capture.
    """
    return [m for m in generate_legal_moves(board)
            if not board.is_empty(m.to_sq) or m.is_en_passant]
