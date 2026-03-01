"""
utils.py - Utility functions: algebraic-move parsing, perft, and helpers.

Perft (Performance Test)
------------------------
perft(board, depth) counts the number of leaf nodes at *depth* plies,
exercising move generation and make/undo_move correctness.

Expected values from the standard starting position:
  Depth 1 :          20 nodes
  Depth 2 :         400 nodes
  Depth 3 :       8,902 nodes
  Depth 4 :     197,281 nodes
  Depth 5 :   4,865,609 nodes

See https://www.chessprogramming.org/Perft_Results for full reference.
"""

from __future__ import annotations
import time
from typing import Optional

from board import Board
from move import Move
from move_generator import generate_legal_moves


# ──────────────────────────────────────────────────────────────────────────────
# Move parsing
# ──────────────────────────────────────────────────────────────────────────────

def parse_uci_move(board: Board, uci: str) -> Optional[Move]:
    """
    Parse a UCI long-algebraic move string (e.g. 'e2e4', 'e7e8q') and
    return the matching legal Move object, or None if the move is illegal.

    Parameters
    ----------
    board : Board
        Current board (used to validate legality).
    uci : str
        Move string: 4 or 5 characters.

    Returns
    -------
    Move or None
    """
    uci = uci.strip().lower()
    if len(uci) not in (4, 5):
        return None

    try:
        from_sq = _alg_to_sq(uci[:2])
        to_sq   = _alg_to_sq(uci[2:4])
    except (ValueError, IndexError):
        return None

    promotion = uci[4].upper() if len(uci) == 5 else None

    # Match against generated legal moves
    for move in generate_legal_moves(board):
        if move.from_sq == from_sq and move.to_sq == to_sq:
            if promotion is None or move.promotion == promotion:
                return move
    return None


def _alg_to_sq(alg: str) -> int:
    """Convert 'e4' → board index."""
    if len(alg) != 2 or alg[0] not in "abcdefgh" or alg[1] not in "12345678":
        raise ValueError(f"Invalid square: {alg!r}")
    return (int(alg[1]) - 1) * 8 + (ord(alg[0]) - ord("a"))


# ──────────────────────────────────────────────────────────────────────────────
# Perft
# ──────────────────────────────────────────────────────────────────────────────

def perft(board: Board, depth: int) -> int:
    """
    Count leaf nodes at exactly *depth* plies from the current position.

    This is the standard correctness benchmark for move generators.
    At depth 1 it simply counts the legal moves available.

    Parameters
    ----------
    board : Board
        Position to search from.
    depth : int
        Number of plies to search.

    Returns
    -------
    int
        Total number of leaf nodes.
    """
    if depth == 0:
        return 1

    legal_moves = generate_legal_moves(board)
    total = 0

    for move in legal_moves:
        undo = board.make_move(move)
        total += perft(board, depth - 1)
        board.undo_move(move, undo)

    return total


def perft_divide(board: Board, depth: int) -> dict:
    """
    Run perft at *depth* and return a dict {move_uci: node_count}.

    Useful for debugging: compare against a reference engine move-by-move.
    """
    results = {}
    for move in generate_legal_moves(board):
        undo = board.make_move(move)
        count = perft(board, depth - 1)
        board.undo_move(move, undo)
        results[str(move)] = count
    return results


def run_perft_suite(fen: str | None = None, max_depth: int = 3) -> None:
    """
    Run perft from depth 1 to *max_depth* and print results with timing.

    Expected results from the standard starting position:
      Depth 1 →     20
      Depth 2 →    400
      Depth 3 →  8,902

    Parameters
    ----------
    fen : str or None
        FEN string; uses starting position if None.
    max_depth : int
        Maximum depth to test (depth 4+ can be slow).
    """
    from board import STARTING_FEN

    fen = fen or STARTING_FEN
    board = Board.from_fen(fen)

    EXPECTED = {1: 20, 2: 400, 3: 8902, 4: 197281, 5: 4865609}

    print(f"\nPerft from: {fen}")
    print(f"{'Depth':>6}  {'Nodes':>12}  {'Expected':>12}  {'Time':>8}  Status")
    print("-" * 60)

    for d in range(1, max_depth + 1):
        board = Board.from_fen(fen)
        t0 = time.time()
        nodes = perft(board, d)
        elapsed = time.time() - t0

        expected = EXPECTED.get(d, "?")
        status = ""
        if isinstance(expected, int):
            status = "✓" if nodes == expected else f"✗ (expected {expected:,})"
        print(f"{d:>6}  {nodes:>12,}  {str(expected):>12}  {elapsed:>7.3f}s  {status}")

    print()
