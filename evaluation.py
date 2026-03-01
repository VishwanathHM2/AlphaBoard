"""
evaluation.py - Static position evaluation.

Returns a score in centipawns from White's perspective:
  Positive → White is better
  Negative → Black is better

Components
----------
1. Material balance
2. Piece-square table bonuses
3. Mobility bonus (number of legal moves)

All piece-square tables are defined in constants.py and indexed
rank-8-first (index 0 = a8).  For White, we map board index directly.
For Black, we mirror vertically so they share the same table.
"""

from __future__ import annotations

from constants import WHITE, BLACK, EMPTY, PIECE_VALUES, WHITE_PST, rank_of, file_of
from board import Board
from move_generator import generate_legal_moves


def _pst_score(piece: str, board_idx: int) -> int:
    """
    Return the piece-square table bonus for *piece* at *board_idx*.

    The tables are stored rank-8-first (a8=0, h8=7, a7=8, …, h1=63).
    Board indices are rank-1-first (a1=0, …, h8=63).

    For White: flip vertically so that rank 1 maps to table row 7.
    For Black: use board index directly (table already "looks right"
               from Black's perspective when flipped, but since Black
               pieces share White's bonus values, we mirror as well).
    """
    pc_upper = piece.upper()
    if pc_upper not in WHITE_PST:
        return 0

    table = WHITE_PST[pc_upper]
    rank = rank_of(board_idx)
    file = file_of(board_idx)

    if piece.isupper():
        # White: table index has rank-8 first → mirror rank
        idx = (7 - rank) * 8 + file
    else:
        # Black: mirror file-symmetrically (same table, same rank direction)
        idx = rank * 8 + file

    return table[idx]


def evaluate(board: Board) -> int:
    """
    Return a static evaluation of *board* in centipawns (White-positive).

    Parameters
    ----------
    board : Board
        Position to evaluate.

    Returns
    -------
    int
        Positive favours White; negative favours Black.
    """
    score = 0

    # ── 1. Material + piece-square tables ──
    for i, piece in enumerate(board.squares):
        if piece == EMPTY:
            continue
        value = PIECE_VALUES[piece]
        pst = _pst_score(piece, i)
        if piece.isupper():       # White piece
            score += value + pst
        else:                     # Black piece
            score -= value + pst

    # ── 2. Mobility bonus (5 cp per extra legal move) ──
    # We only compute a cheap approximation: count legal moves for
    # the current side, then negate for the opponent.  Full mobility
    # for both sides would double the legal-move generation cost.
    current_mobility = len(generate_legal_moves(board))
    mobility_bonus = current_mobility * 5
    if board.side_to_move == WHITE:
        score += mobility_bonus
    else:
        score -= mobility_bonus

    return score
