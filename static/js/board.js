/**
 * board.js
 * Handles all DOM operations for the chess board:
 *   - Building the 8×8 grid
 *   - Rendering pieces, highlights, legal-move dots, coordinate labels
 *
 * Does NOT contain game logic — it only reads from the shared `state`
 * object (defined in game.js) and calls back via onSquareClick().
 */

/** Build (or rebuild) the entire board DOM. Called on new game or side change. */
function buildBoard() {
  const boardEl = document.getElementById('board');
  boardEl.innerHTML = '';

  for (let visual = 0; visual < 64; visual++) {
    const sq = visualToSq(visual);
    const div = document.createElement('div');
    const lightDark = ((Math.floor(visual / 8) + (visual % 8)) % 2 === 0) ? 'dark' : 'light';
    div.className = `sq ${lightDark}`;
    div.dataset.sq = sq;
    div.addEventListener('click', () => onSquareClick(sq));
    boardEl.appendChild(div);
  }

  buildCoords();
}

/**
 * Convert a visual grid index (0 = top-left as seen by the player)
 * to a board square index (0 = a1).
 */
function visualToSq(visual) {
  const row = Math.floor(visual / 8);
  const col = visual % 8;
  if (state.humanSide === 'white') {
    return (7 - row) * 8 + col;
  } else {
    return row * 8 + (7 - col);
  }
}

/** Re-render every square: piece, highlights, legal dots. */
function renderBoard() {
  const squares = parseFenSquares(state.fen);
  const side = fenSide(state.fen);

  document.querySelectorAll('.sq').forEach(el => {
    const sq = +el.dataset.sq;
    const pc = squares[sq];

    // Base colour class
    const isLight = ((Math.floor(el.dataset.sq / 8) + (el.dataset.sq % 8)) % 2 !== 0);
    el.className = 'sq ' + (isLight ? 'light' : 'dark');

    // Highlights
    if (sq === state.selectedSq)  el.classList.add('selected');
    if (sq === state.lastFrom)    el.classList.add('last-from');
    if (sq === state.lastTo)      el.classList.add('last-to');

    // Check
    const kingChar = side === 'white' ? 'K' : 'k';
    if (pc === kingChar && state.inCheck) el.classList.add('in-check');

    // Legal-move dots for the selected piece
    if (state.selectedSq !== null) {
      const isTarget = state.legalMoves.some(
        m => m.from_sq === state.selectedSq && m.to_sq === sq
      );
      if (isTarget) {
        el.classList.add(pc !== '.' ? 'legal-capture' : 'legal-target');
      }
    }

    // Piece glyph
    el.innerHTML = pc !== '.' ? `<span class="piece">${UNICODE[pc] || ''}</span>` : '';
  });
}

/** Build file (a–h) and rank (1–8) coordinate labels. */
function buildCoords() {
  const fileRow  = document.getElementById('file-coords');
  const rankCol  = document.getElementById('rank-coords');
  fileRow.innerHTML = '';
  rankCol.innerHTML = '';

  const files = state.humanSide === 'white' ? 'abcdefgh' : 'hgfedcba';
  for (const f of files) {
    const d = document.createElement('div');
    d.className = 'coord-file';
    d.textContent = f;
    fileRow.appendChild(d);
  }

  const sqSize = document.querySelector('.sq')?.offsetHeight || 64;
  for (let i = 0; i < 8; i++) {
    const r = state.humanSide === 'white' ? 8 - i : i + 1;
    const d = document.createElement('div');
    d.className = 'coord-rank';
    d.style.height = sqSize + 'px';
    d.textContent = r;
    rankCol.appendChild(d);
  }
}

// ── FEN parsing helpers (lightweight, UI-side only) ──────────────────────────

/** Parse FEN piece placement → 64-element array of piece chars / '.' */
function parseFenSquares(fen) {
  const squares = Array(64).fill('.');
  const ranks = fen.split(' ')[0].split('/');
  for (let ri = 0; ri < 8; ri++) {
    let fi = 0;
    for (const ch of ranks[ri]) {
      if ('12345678'.includes(ch)) { fi += +ch; }
      else { squares[(7 - ri) * 8 + fi] = ch; fi++; }
    }
  }
  return squares;
}

/** Return 'white' or 'black' from a FEN string. */
function fenSide(fen) {
  return fen.split(' ')[1] === 'w' ? 'white' : 'black';
}
