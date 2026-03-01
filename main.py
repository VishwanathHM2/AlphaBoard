"""
main.py - CLI interface for the Python chess engine.

Usage
-----
  python main.py                  # Human (White) vs Engine (Black), depth 4
  python main.py --depth 3        # Engine searches to depth 3
  python main.py --engine-white   # Engine plays White, Human plays Black
  python main.py --perft 3        # Run perft suite to depth 3 and exit
  python main.py --fen "<FEN>"    # Start from a custom FEN position

Move input format: UCI long-algebraic, e.g.  e2e4  d7d5  e7e8q

Type 'quit' or 'q' to exit.
Type 'board' to redisplay the board.
Type 'moves' to list all legal moves.
Type 'undo' to take back the last move.
"""

import argparse
import sys

from board import Board, STARTING_FEN
from move_generator import generate_legal_moves, is_in_check
from search import find_best_move
from utils import parse_uci_move, run_perft_suite
from constants import WHITE, BLACK


# ──────────────────────────────────────────────────────────────────────────────
# Game loop helpers
# ──────────────────────────────────────────────────────────────────────────────

def print_board(board: Board) -> None:
    print()
    print(board.display())
    print()


def check_game_over(board: Board) -> str | None:
    """
    Return a result string if the game is over, else None.
      '1-0'     White wins (Black is in checkmate)
      '0-1'     Black wins (White is in checkmate)
      '1/2-1/2' Draw (stalemate or fifty-move rule)
    """
    legal = generate_legal_moves(board)
    if legal:
        if board.halfmove_clock >= 100:
            return "1/2-1/2 (fifty-move rule)"
        return None
    # No legal moves
    if is_in_check(board, board.side_to_move):
        if board.side_to_move == WHITE:
            return "0-1 (Black wins by checkmate)"
        else:
            return "1-0 (White wins by checkmate)"
    return "1/2-1/2 (stalemate)"


# ──────────────────────────────────────────────────────────────────────────────
# Human move input
# ──────────────────────────────────────────────────────────────────────────────

def get_human_move(board: Board) -> str | None:
    """
    Prompt the human player for a move.

    Returns the UCI string on a successful legal move, or None on quit.
    Handles special commands (board / moves / quit).
    """
    while True:
        try:
            raw = input("Your move (e.g. e2e4): ").strip()
        except (EOFError, KeyboardInterrupt):
            return None

        cmd = raw.lower()

        if cmd in ("q", "quit", "exit"):
            return None

        if cmd == "board":
            print_board(board)
            continue

        if cmd == "moves":
            legal = generate_legal_moves(board)
            print("Legal moves:", " ".join(sorted(str(m) for m in legal)))
            continue

        move = parse_uci_move(board, raw)
        if move is None:
            print(f"  Illegal or unrecognised move: {raw!r}. Try again.")
            continue

        return raw   # return the raw string; caller re-parses if needed


# ──────────────────────────────────────────────────────────────────────────────
# Main game loop
# ──────────────────────────────────────────────────────────────────────────────

def play(fen: str, engine_side: str, depth: int) -> None:
    """
    Run a full game loop.

    Parameters
    ----------
    fen : str       Starting FEN.
    engine_side : str  'white' or 'black'.
    depth : int     Engine search depth.
    """
    board = Board.from_fen(fen)
    history = []   # list of (move, undo_info) for undo support

    human_side = BLACK if engine_side == WHITE else WHITE
    print(f"\nChess Engine  |  You play {'White' if human_side == WHITE else 'Black'}  "
          f"|  Engine depth {depth}\n")
    print("Commands: quit | board | moves | undo")
    print_board(board)

    while True:
        result = check_game_over(board)
        if result:
            print(f"\nGame over: {result}")
            break

        side_name = "White" if board.side_to_move == WHITE else "Black"

        # ── Engine's turn ──
        if board.side_to_move == engine_side:
            print(f"{side_name} (engine) is thinking...")
            move = find_best_move(board, max_depth=depth)
            if move is None:
                print("Engine has no move (shouldn't happen here).")
                break
            undo = board.make_move(move)
            history.append((move, undo))
            print(f"{side_name} plays: {move}")
            print_board(board)

        # ── Human's turn ──
        else:
            in_check = is_in_check(board, board.side_to_move)
            if in_check:
                print(f"  *** {side_name} is in CHECK ***")

            raw = get_human_move(board)
            if raw is None:
                print("\nGoodbye!")
                break

            # Handle undo
            if raw.lower() == "undo":
                if len(history) < 2:
                    print("  Nothing to undo.")
                    continue
                # Undo last two plies (engine + human)
                for _ in range(2):
                    if history:
                        m, u = history.pop()
                        board.undo_move(m, u)
                print("  Undone two half-moves.")
                print_board(board)
                continue

            move = parse_uci_move(board, raw)
            if move is None:
                print(f"  Illegal move: {raw!r}")
                continue
            undo = board.make_move(move)
            history.append((move, undo))
            print_board(board)


# ──────────────────────────────────────────────────────────────────────────────
# Argument parsing & entry point
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Python chess engine – Level 2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--depth", type=int, default=4,
                        help="Engine search depth (default: 4)")
    parser.add_argument("--engine-white", action="store_true",
                        help="Engine plays White (human plays Black)")
    parser.add_argument("--fen", type=str, default=STARTING_FEN,
                        help="Starting FEN position")
    parser.add_argument("--perft", type=int, metavar="DEPTH",
                        help="Run perft suite to DEPTH and exit")
    args = parser.parse_args()

    if args.perft:
        run_perft_suite(fen=args.fen, max_depth=args.perft)
        sys.exit(0)

    engine_side = WHITE if args.engine_white else BLACK
    play(fen=args.fen, engine_side=engine_side, depth=args.depth)


if __name__ == "__main__":
    main()
