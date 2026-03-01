/**
 * game.js
 * Core game controller.  Owns the shared `state` object and orchestrates
 * interactions between the board renderer (board.js), the UI helpers (ui.js)
 * and the Python engine via the API client (api.js).
 *
 * Flow
 * ────
 * 1. User clicks a square           → onSquareClick()
 * 2. Legal moves fetched from server → renderBoard() highlights targets
 * 3. User clicks a target square    → applyHumanMove()
 * 4. New FEN sent to /api/move      → engine returns best move
 * 5. Board updated with engine move → back to step 1
 */

// ── Shared state ──────────────────────────────────────────────────────────────

const state = {
  fen:            STARTING_FEN,
  humanSide:      'white',
  engineThinking: false,

  // Selection
  selectedSq:   null,
  legalMoves:   [],      // full move objects for current position

  // Highlights
  lastFrom: -1,
  lastTo:   -1,

  // Check flag (set after each status poll)
  inCheck: false,

  // History / captured
  moveHistory:       [],   // [{uci, isEngine}]
  capturedByEngine:  [],
  capturedByHuman:   [],

  // Undo stack (stores FEN snapshots before each human+engine pair)
  undoStack: [],
};

// ── New game ──────────────────────────────────────────────────────────────────

async function newGame() {
  state.fen            = STARTING_FEN;
  state.selectedSq     = null;
  state.legalMoves     = [];
  state.lastFrom       = -1;
  state.lastTo         = -1;
  state.inCheck        = false;
  state.engineThinking = false;
  state.moveHistory       = [];
  state.capturedByEngine  = [];
  state.capturedByHuman   = [];
  state.undoStack         = [];

  hideOverlay();
  hideThinkingBar();

  buildBoard();
  renderBoard();
  renderHistory();
  updateCaptured();
  setStatus('Your turn (White)');

  // If engine plays White, let it move first
  if (state.humanSide === 'black') {
    await doEngineMove();
  } else {
    // Pre-fetch legal moves so dots appear immediately on first click
    await refreshLegalMoves();
  }
}

// ── Square click handler ──────────────────────────────────────────────────────

async function onSquareClick(sq) {
  if (state.engineThinking) return;
  if (fenSide(state.fen) !== state.humanSide) return;

  const squares = parseFenSquares(state.fen);
  const pc = squares[sq];

  // ── A square is already selected ──
  if (state.selectedSq !== null) {
    // Find any legal move from selectedSq → sq
    const candidates = state.legalMoves.filter(
      m => m.from_sq === state.selectedSq && m.to_sq === sq
    );

    if (candidates.length > 0) {
      // Promotion? multiple candidates with different promotion pieces
      if (candidates.some(m => m.promotion)) {
        const chosen = await promptPromotion(state.humanSide);
        const mv = candidates.find(m => m.promotion === chosen) || candidates[0];
        await applyHumanMove(mv);
      } else {
        await applyHumanMove(candidates[0]);
      }
      return;
    }

    // Re-select own piece
    if (isFriendly(pc, state.humanSide)) {
      state.selectedSq = sq;
      renderBoard();
      return;
    }

    // Click on empty / enemy with no legal move → deselect
    state.selectedSq = null;
    renderBoard();
    return;
  }

  // ── First click: select own piece ──
  if (isFriendly(pc, state.humanSide)) {
    state.selectedSq = sq;
    renderBoard();
  }
}

// ── Apply a human move ────────────────────────────────────────────────────────

async function applyHumanMove(mv) {
  // Save snapshot for undo (before human move)
  state.undoStack.push({
    fen:               state.fen,
    moveHistory:       [...state.moveHistory],
    capturedByEngine:  [...state.capturedByEngine],
    capturedByHuman:   [...state.capturedByHuman],
    lastFrom:          state.lastFrom,
    lastTo:            state.lastTo,
  });

  // Derive captured piece from current FEN
  const squares = parseFenSquares(state.fen);
  const captured = squares[mv.to_sq];
  if (captured && captured !== '.') {
    state.capturedByHuman.push(captured);
  }

  // Apply move: update FEN client-side without a round-trip
  // The engine move endpoint returns new_fen; for human moves we
  // derive the new FEN by sending to /api/status (which accepts any FEN).
  // Simplest approach: just store the move and let server confirm via status.
  state.fen = applyMoveToFen(state.fen, mv);

  state.lastFrom   = mv.from_sq;
  state.lastTo     = mv.to_sq;
  state.selectedSq = null;
  state.legalMoves = [];

  addMoveToHistory(mv.uci, false);
  renderBoard();
  updateCaptured();

  // Check status
  const status = await API.getStatus(state.fen);
  state.inCheck = status.in_check;
  renderBoard();

  if (checkGameOver(status)) return;
  updateStatus(status);

  // Engine's turn
  await doEngineMove();
}

// ── Engine move ───────────────────────────────────────────────────────────────

async function doEngineMove() {
  if (fenSide(state.fen) === state.humanSide) return;

  state.engineThinking = true;
  showThinkingBar();
  const side = fenSide(state.fen);
  setStatus(`${side === 'white' ? 'White' : 'Black'} (engine) is thinking…`, true);

  try {
    const depth = parseInt(document.getElementById('depth-select').value, 10);
    const mv    = await API.getMove(state.fen, depth);

    // Capture tracking
    const squares  = parseFenSquares(state.fen);
    const captured = squares[mv.to_sq];
    if (captured && captured !== '.') state.capturedByEngine.push(captured);

    state.fen    = mv.new_fen;
    state.lastFrom = mv.from_sq;
    state.lastTo   = mv.to_sq;

    addMoveToHistory(mv.uci, true);
    updateCaptured();

    // Status check
    const status = await API.getStatus(state.fen);
    state.inCheck = status.in_check;
    renderBoard();

    if (checkGameOver(status)) return;
    updateStatus(status);

    // Refresh legal moves for human
    await refreshLegalMoves();

  } catch (err) {
    setStatus(`Engine error: ${err.message}`);
    console.error(err);
  } finally {
    state.engineThinking = false;
    hideThinkingBar();
  }
}

// ── Undo ──────────────────────────────────────────────────────────────────────

async function undoMove() {
  if (state.engineThinking || state.undoStack.length === 0) return;

  // Pop one snapshot (restores position before last human move,
  // which also rolls back the engine's reply since the engine move
  // snapshot was pushed before the human move)
  const snap = state.undoStack.pop();
  state.fen              = snap.fen;
  state.moveHistory      = snap.moveHistory;
  state.capturedByEngine = snap.capturedByEngine;
  state.capturedByHuman  = snap.capturedByHuman;
  state.lastFrom         = snap.lastFrom;
  state.lastTo           = snap.lastTo;
  state.selectedSq       = null;
  state.inCheck          = false;

  renderHistory();
  updateCaptured();

  const status = await API.getStatus(state.fen);
  state.inCheck = status.in_check;
  updateStatus(status);

  await refreshLegalMoves();
  renderBoard();
}

// ── Helpers ───────────────────────────────────────────────────────────────────

async function refreshLegalMoves() {
  try {
    state.legalMoves = await API.getLegalMoves(state.fen);
  } catch (e) {
    state.legalMoves = [];
  }
  renderBoard();
}

function isFriendly(pc, side) {
  if (!pc || pc === '.') return false;
  return side === 'white' ? pc >= 'A' && pc <= 'Z' : pc >= 'a' && pc <= 'z';
}

/**
 * Apply a move object to a FEN string and return the updated FEN.
 *
 * This is a lightweight client-side implementation used for human moves
 * so we can update the board instantly without a round-trip.  The Python
 * engine is the authoritative source of truth; the server always returns
 * the canonical new_fen for engine moves.
 */
function applyMoveToFen(fen, mv) {
  const squares = parseFenSquares(fen);
  const parts   = fen.split(' ');
  const side    = parts[1] === 'w' ? 'white' : 'black';

  let pc = squares[mv.from_sq];

  // En passant capture
  if (mv.is_en_passant) {
    const capSq = side === 'white' ? mv.to_sq - 8 : mv.to_sq + 8;
    squares[capSq] = '.';
  }

  // Castling rook
  if (mv.is_castling) {
    const rookMoves = {
      6:  [7,  5],   // White kingside
      2:  [0,  3],   // White queenside
      62: [63, 61],  // Black kingside
      58: [56, 59],  // Black queenside
    };
    const [rookFrom, rookTo] = rookMoves[mv.to_sq] || [];
    if (rookFrom !== undefined) {
      squares[rookTo]   = squares[rookFrom];
      squares[rookFrom] = '.';
    }
  }

  // Promotion
  if (mv.promotion) {
    pc = side === 'white' ? mv.promotion.toUpperCase() : mv.promotion.toLowerCase();
  }

  squares[mv.to_sq]   = pc;
  squares[mv.from_sq] = '.';

  // Rebuild FEN piece string
  let fenPieces = '';
  for (let rank = 7; rank >= 0; rank--) {
    let empty = 0;
    for (let file = 0; file < 8; file++) {
      const p = squares[rank * 8 + file];
      if (p === '.') { empty++; }
      else { if (empty) { fenPieces += empty; empty = 0; } fenPieces += p; }
    }
    if (empty) fenPieces += empty;
    if (rank > 0) fenPieces += '/';
  }

  // Side to move
  const newSide = side === 'white' ? 'b' : 'w';

  // En passant target
  let ep = '-';
  if (pc.toUpperCase() === 'P') {
    const fromRank = Math.floor(mv.from_sq / 8);
    const toRank   = Math.floor(mv.to_sq   / 8);
    if (Math.abs(toRank - fromRank) === 2) {
      const epRank = (fromRank + toRank) >> 1;
      const epFile = mv.to_sq % 8;
      ep = String.fromCharCode(97 + epFile) + (epRank + 1);
    }
  }

  // Castling rights (simplified: revoke on king/rook moves)
  let cast = parts[2];
  const revoke = (flag, sq) => { if (mv.from_sq === sq || mv.to_sq === sq) cast = cast.replace(flag, ''); };
  if (mv.from_sq === 4  || mv.to_sq === 4)  cast = cast.replace('K','').replace('Q','');
  if (mv.from_sq === 60 || mv.to_sq === 60) cast = cast.replace('k','').replace('q','');
  revoke('K', 7);  revoke('Q', 0);
  revoke('k', 63); revoke('q', 56);
  if (!cast) cast = '-';

  // Halfmove / fullmove
  const half = (pc.toUpperCase() === 'P' || squares[mv.to_sq] !== '.') ? 0 : parseInt(parts[4]) + 1;
  const full = side === 'black' ? parseInt(parts[5]) + 1 : parseInt(parts[5]);

  return `${fenPieces} ${newSide} ${cast} ${ep} ${half} ${full}`;
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => newGame());
