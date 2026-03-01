"""
server.py - Flask web server bridging the chess engine to the browser UI.

Endpoints
---------
GET  /                  Serve the main HTML page
POST /api/move          Ask the engine for its best move
POST /api/legal_moves   Return all legal moves for the current position
POST /api/status        Return check / checkmate / stalemate status
"""

from flask import Flask, render_template, request, jsonify

from board import Board, STARTING_FEN
from move_generator import generate_legal_moves, is_in_check
from search import find_best_move
from constants import WHITE, BLACK

app = Flask(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def board_from_request() -> Board:
    """
    Reconstruct a Board from the FEN string in the JSON request body.
    Raises ValueError if FEN is missing or malformed.
    """
    data = request.get_json(force=True)
    fen = data.get("fen")
    if not fen:
        raise ValueError("Missing 'fen' field in request body.")
    return Board.from_fen(fen)


def move_to_dict(move) -> dict:
    """Serialise a Move object to a JSON-safe dict."""
    return {
        "uci":          move.to_uci(),
        "from_sq":      move.from_sq,
        "to_sq":        move.to_sq,
        "promotion":    move.promotion,
        "is_en_passant":move.is_en_passant,
        "is_castling":  move.is_castling,
    }


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main chess UI page."""
    return render_template("index.html")


@app.route("/api/move", methods=["POST"])
def api_move():
    """
    Ask the engine for its best move.

    Request JSON
    ------------
    {
        "fen":   "<FEN string>",
        "depth": <int, optional, default 4>
    }

    Response JSON
    -------------
    {
        "move":     "<uci string>",   // e.g. "e2e4"
        "from_sq":  <int>,
        "to_sq":    <int>,
        "promotion": <str|null>,
        "is_en_passant": <bool>,
        "is_castling":   <bool>,
        "new_fen":  "<FEN after move>"
    }
    """
    try:
        data = request.get_json(force=True)
        fen = data.get("fen", STARTING_FEN)
        depth = int(data.get("depth", 4))
        depth = max(1, min(depth, 6))   # clamp to sane range

        board = Board.from_fen(fen)
        best = find_best_move(board, max_depth=depth)

        if best is None:
            return jsonify({"error": "No legal moves available"}), 400

        board.make_move(best)
        result = move_to_dict(best)
        result["new_fen"] = board.to_fen()
        return jsonify(result)

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/legal_moves", methods=["POST"])
def api_legal_moves():
    """
    Return all legal moves from a given FEN position.

    Request JSON  : { "fen": "<FEN>" }
    Response JSON : { "moves": [ { "uci", "from_sq", "to_sq", ... }, … ] }
    """
    try:
        board = board_from_request()
        moves = generate_legal_moves(board)
        return jsonify({"moves": [move_to_dict(m) for m in moves]})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/status", methods=["POST"])
def api_status():
    """
    Return the game status for a given FEN position.

    Request JSON  : { "fen": "<FEN>" }
    Response JSON :
    {
        "in_check":    <bool>,
        "checkmate":   <bool>,
        "stalemate":   <bool>,
        "game_over":   <bool>,
        "result":      <str|null>,   // "1-0" / "0-1" / "1/2-1/2" / null
        "side_to_move": "white"|"black"
    }
    """
    try:
        board = board_from_request()
        legal = generate_legal_moves(board)
        check = is_in_check(board, board.side_to_move)
        checkmate = check and not legal
        stalemate = not check and not legal
        game_over = checkmate or stalemate

        result = None
        if checkmate:
            result = "0-1" if board.side_to_move == WHITE else "1-0"
        elif stalemate:
            result = "1/2-1/2"

        return jsonify({
            "in_check":     check,
            "checkmate":    checkmate,
            "stalemate":    stalemate,
            "game_over":    game_over,
            "result":       result,
            "side_to_move": board.side_to_move,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Chess Engine server running → http://localhost:5000")
    app.run(debug=False, port=5000)
