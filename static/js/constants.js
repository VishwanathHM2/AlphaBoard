/**
 * constants.js
 * Shared lookup tables used across all JS modules.
 */

const UNICODE = {
  P: '♙', N: '♘', B: '♗', R: '♖', Q: '♕', K: '♔',
  p: '♟', n: '♞', b: '♝', r: '♜', q: '♛', k: '♚',
  '.': ''
};

const STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

/** Map square index → algebraic string (e.g. 4 → "e1") */
function sqToAlg(sq) {
  return String.fromCharCode(97 + (sq % 8)) + (Math.floor(sq / 8) + 1);
}
