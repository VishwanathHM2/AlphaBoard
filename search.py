"""
search.py - Chess search engine.

Implements:
  - Minimax with alpha-beta pruning
  - Iterative deepening (searches depth 1, 2, … up to max_depth)
  - Quiescence search (avoids horizon effect at leaf nodes)
  - Move ordering (MVV-LVA for captures, promotions first)

Alpha-Beta Pruning Explained
-----------------------------
Standard minimax visits every node in the search tree.  Alpha-beta
avoids branches that cannot possibly affect the result:

  alpha = the best score the maximiser (White) has found so far.
  beta  = the best score the minimiser (Black) has found so far.

  If a node's score >= beta  → the minimiser already has a refutation;
                               prune this subtree (beta cut-off).
  If a node's score <= alpha → the maximiser already has something
                               better; prune this subtree (alpha cut-off).

In the best case (perfect move ordering) alpha-beta reduces the
branching factor from b to √b, allowing twice the search depth.

Quiescence Search Explained
----------------------------
At depth 0 the normal search stops and calls the static evaluator.
But if the position is "noisy" (captures available), the static score
can be misleading — e.g. we just moved our queen to a square where it
will immediately be taken.  Quiescence search extends the search with
capture-only moves until a "quiet" position is reached, preventing
this horizon effect.

A stand-pat score (static eval) provides a lower bound: if even without
capturing we already beat beta, we can prune immediately.
"""

from __future__ import annotations
from typing import Optional, Tuple
import time

from constants import WHITE, BLACK, INF, PIECE_VALUES, EMPTY
from board import Board
from move import Move
from move_generator import generate_legal_moves, generate_capture_moves, is_in_check
from evaluation import evaluate


# ──────────────────────────────────────────────────────────────────────────────
# Move ordering
# ──────────────────────────────────────────────────────────────────────────────

def _mvv_lva_score(board: Board, move: Move) -> int:
    """
    Most-Valuable-Victim / Least-Valuable-Attacker score for capture ordering.

    Higher score → search this move first.
    Promotions are given a high bonus so they are tried early.
    """
    if move.promotion:
        return 20000 + PIECE_VALUES.get(move.promotion, 0)

    victim = board.squares[move.to_sq]
    if move.is_en_passant:
        victim = "p" if board.side_to_move == WHITE else "P"

    if victim == EMPTY:
        return 0   # quiet move

    attacker = board.squares[move.from_sq]
    # Maximise victim value, minimise attacker value
    return PIECE_VALUES.get(victim.upper(), 0) * 10 - PIECE_VALUES.get(attacker.upper(), 0)


def _order_moves(board: Board, moves: list) -> list:
    """
    Return moves sorted best-first using MVV-LVA.

    Captures and promotions are sorted before quiet moves.
    Within captures, high-value victim / low-value attacker first.
    """
    return sorted(moves, key=lambda m: _mvv_lva_score(board, m), reverse=True)


# ──────────────────────────────────────────────────────────────────────────────
# Quiescence search
# ──────────────────────────────────────────────────────────────────────────────

def quiescence(board: Board, alpha: int, beta: int) -> int:
    """
    Quiescence search: extend with captures only until position is quiet.

    The "stand-pat" score lets us assume we can always choose *not* to
    capture, which gives a lower bound on the position's true value.

    Parameters
    ----------
    board : Board
    alpha : int   Lower bound (maximiser's best so far)
    beta  : int   Upper bound (minimiser's best so far)

    Returns
    -------
    int   Score from the current side-to-move's perspective (White-positive).
    """
    stand_pat = evaluate(board)  # static eval (White-positive)

    # Stand-pat pruning: if the quiet position already beats beta, stop.
    if stand_pat >= beta:
        return beta

    if stand_pat > alpha:
        alpha = stand_pat   # update lower bound

    captures = generate_capture_moves(board)
    captures = _order_moves(board, captures)

    for move in captures:
        undo = board.make_move(move)
        score = -quiescence(board, -beta, -alpha)
        board.undo_move(move, undo)

        if score >= beta:
            return beta   # beta cut-off
        if score > alpha:
            alpha = score

    return alpha


# ──────────────────────────────────────────────────────────────────────────────
# Alpha-beta search
# ──────────────────────────────────────────────────────────────────────────────

def alpha_beta(board: Board, depth: int, alpha: int, beta: int,
               maximizing_player: bool) -> int:
    """
    Minimax with alpha-beta pruning.

    Scores are always White-positive (engine always maximises for White).

    Parameters
    ----------
    board : Board
        Current position.
    depth : int
        Remaining plies to search.  0 → quiescence search.
    alpha : int
        Best score the maximiser has found along the path to the root.
    beta : int
        Best score the minimiser has found along the path to the root.
    maximizing_player : bool
        True if we are maximising (White to move).

    Returns
    -------
    int
        Evaluation score from White's perspective.
    """
    # ── Terminal / leaf node ──
    if depth == 0:
        # Enter quiescence search instead of a bare static eval
        return quiescence(board, alpha, beta)

    legal_moves = generate_legal_moves(board)

    # ── No legal moves: checkmate or stalemate ──
    if not legal_moves:
        if is_in_check(board, board.side_to_move):
            # Checkmate: side-to-move loses.  Prefer earlier mates (depth bonus).
            if maximizing_player:
                return -INF + (100 - depth)
            else:
                return INF - (100 - depth)
        else:
            return 0  # Stalemate

    legal_moves = _order_moves(board, legal_moves)

    if maximizing_player:
        best = -INF
        for move in legal_moves:
            undo = board.make_move(move)
            score = alpha_beta(board, depth - 1, alpha, beta, False)
            board.undo_move(move, undo)

            best = max(best, score)
            alpha = max(alpha, best)
            if alpha >= beta:
                break   # ← beta cut-off: minimiser would avoid this branch
        return best
    else:
        best = INF
        for move in legal_moves:
            undo = board.make_move(move)
            score = alpha_beta(board, depth - 1, alpha, beta, True)
            board.undo_move(move, undo)

            best = min(best, score)
            beta = min(beta, best)
            if beta <= alpha:
                break   # ← alpha cut-off: maximiser would avoid this branch
        return best


# ──────────────────────────────────────────────────────────────────────────────
# Iterative deepening
# ──────────────────────────────────────────────────────────────────────────────

def find_best_move(board: Board, max_depth: int = 4,
                   time_limit: float = 10.0) -> Optional[Move]:
    """
    Find the best move using iterative deepening alpha-beta.

    Searches at depth 1, 2, … up to *max_depth* (or until *time_limit*
    seconds have elapsed).  Using the result from a shallower search as
    the starting move-ordering hint for the next iteration improves pruning.

    Parameters
    ----------
    board : Board
    max_depth : int
        Maximum search depth (plies).
    time_limit : float
        Wall-clock seconds budget.

    Returns
    -------
    Move or None
        Best move found, or None if no legal moves exist.
    """
    legal_moves = generate_legal_moves(board)
    if not legal_moves:
        return None

    start_time = time.time()
    maximizing = (board.side_to_move == WHITE)
    best_move: Optional[Move] = None

    for depth in range(1, max_depth + 1):
        if time.time() - start_time > time_limit:
            break   # time budget exhausted

        current_best_move: Optional[Move] = None
        current_best_score = -INF if maximizing else INF

        # Order moves using result from previous iteration (if any)
        ordered = _order_moves(board, legal_moves)

        for move in ordered:
            undo = board.make_move(move)
            score = alpha_beta(board, depth - 1, -INF, INF, not maximizing)
            board.undo_move(move, undo)

            if maximizing:
                if score > current_best_score:
                    current_best_score = score
                    current_best_move = move
            else:
                if score < current_best_score:
                    current_best_score = score
                    current_best_move = move

        if current_best_move is not None:
            best_move = current_best_move
            elapsed = time.time() - start_time
            print(f"  [depth {depth}] best={best_move} score={current_best_score:+d} "
                  f"({elapsed:.2f}s)")

    return best_move
