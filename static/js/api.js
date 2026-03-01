/**
 * api.js
 * Thin wrapper around the Flask backend endpoints.
 * All server communication lives here — no fetch() calls elsewhere.
 */

const API = {

  /**
   * Ask the Python engine for its best move.
   * @param {string} fen    - Current board FEN
   * @param {number} depth  - Search depth (1–6)
   * @returns {Promise<{uci, from_sq, to_sq, promotion, is_en_passant, is_castling, new_fen}>}
   */
  async getMove(fen, depth = 4) {
    const res = await fetch('/api/move', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ fen, depth }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `Server error ${res.status}`);
    }
    return res.json();
  },

  /**
   * Fetch all legal moves for the current position.
   * @param {string} fen
   * @returns {Promise<Array<{uci, from_sq, to_sq, promotion, is_en_passant, is_castling}>>}
   */
  async getLegalMoves(fen) {
    const res = await fetch('/api/legal_moves', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ fen }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `Server error ${res.status}`);
    }
    const data = await res.json();
    return data.moves;
  },

  /**
   * Get game-over / check status for a position.
   * @param {string} fen
   * @returns {Promise<{in_check, checkmate, stalemate, game_over, result, side_to_move}>}
   */
  async getStatus(fen) {
    const res = await fetch('/api/status', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ fen }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `Server error ${res.status}`);
    }
    return res.json();
  },
};
