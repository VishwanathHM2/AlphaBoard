/**
 * ui.js
 * Manages all sidebar and overlay UI:
 *   - Status text
 *   - Move history panel
 *   - Captured pieces
 *   - Promotion modal
 *   - Result overlay
 *
 * Reads from and writes to the shared `state` object (game.js).
 */

// ── Status ────────────────────────────────────────────────────────────────────

function setStatus(msg, thinking = false) {
  const el = document.getElementById('status-text');
  el.textContent = msg;
  el.className = thinking ? 'thinking' : '';
}

function updateStatus(statusData) {
  if (state.engineThinking) return;

  if (statusData.game_over) return; // handled by checkGameOver

  const side = statusData.side_to_move;
  const sideLabel = side === 'white' ? 'White' : 'Black';

  if (side === state.humanSide) {
    setStatus(statusData.in_check
      ? `⚠ ${sideLabel} is in CHECK — your move`
      : `Your turn (${sideLabel})`);
  } else {
    setStatus(`${sideLabel} to move`);
  }
}

// ── Thinking bar ─────────────────────────────────────────────────────────────

function showThinkingBar() {
  document.getElementById('thinking-bar').classList.add('active');
}

function hideThinkingBar() {
  document.getElementById('thinking-bar').classList.remove('active');
}

// ── Move history ─────────────────────────────────────────────────────────────

function addMoveToHistory(uci, isEngine) {
  state.moveHistory.push({ uci, isEngine });
  renderHistory();
}

function renderHistory() {
  const el = document.getElementById('move-history');
  if (!state.moveHistory.length) {
    el.innerHTML = '<span style="color:var(--border);font-size:0.7rem">No moves yet</span>';
    return;
  }

  el.innerHTML = '';
  for (let i = 0; i < state.moveHistory.length; i += 2) {
    const white = state.moveHistory[i];
    const black = state.moveHistory[i + 1];
    const row = document.createElement('div');
    row.className = 'move-pair';
    row.innerHTML = `
      <span class="move-num">${Math.floor(i / 2) + 1}.</span>
      <span class="move-cell${white?.isEngine ? ' engine' : ''}">${white?.uci || ''}</span>
      <span class="move-cell${black?.isEngine ? ' engine' : ''}">${black?.uci || ''}</span>
    `;
    el.appendChild(row);
  }
  el.scrollTop = el.scrollHeight;
}

// ── Captured pieces ───────────────────────────────────────────────────────────

function updateCaptured() {
  const fmt = arr => arr.map(p => UNICODE[p] || '').join('');
  document.getElementById('captured-by-engine').textContent = fmt(state.capturedByEngine);
  document.getElementById('captured-by-human').textContent  = fmt(state.capturedByHuman);
}

// ── Result overlay ────────────────────────────────────────────────────────────

function showResult(title, subtitle) {
  document.getElementById('result-title').textContent    = title;
  document.getElementById('result-subtitle').textContent = subtitle;
  document.getElementById('result-overlay').classList.add('show');
}

function hideOverlay() {
  document.getElementById('result-overlay').classList.remove('show');
}

function checkGameOver(statusData) {
  if (!statusData.game_over) return false;

  let title, sub;
  if (statusData.checkmate) {
    const winner = statusData.side_to_move === 'white' ? 'Black' : 'White';
    title = statusData.result === '1-0' ? '1 — 0' : '0 — 1';
    sub   = `${winner} wins by checkmate`;
  } else {
    title = '½ — ½';
    sub   = statusData.stalemate ? 'Stalemate' : 'Draw';
  }

  setTimeout(() => showResult(title, sub), 400);
  return true;
}

// ── Promotion modal ───────────────────────────────────────────────────────────

/**
 * Show the promotion picker and resolve with the chosen piece letter.
 * @param {string} side - 'white' or 'black'
 * @returns {Promise<string>} e.g. 'Q', 'R', 'B', 'N'
 */
function promptPromotion(side) {
  return new Promise(resolve => {
    const pieces  = side === 'white' ? ['Q','R','B','N'] : ['q','r','b','n'];
    const display = ['Q','R','B','N'];

    const container = document.getElementById('promo-choices');
    container.innerHTML = '';

    pieces.forEach((pc, i) => {
      const btn = document.createElement('button');
      btn.className = 'promo-btn';
      btn.textContent = UNICODE[pc] || pc;
      btn.onclick = () => {
        document.getElementById('promo-modal').classList.remove('show');
        resolve(display[i]);   // always return uppercase to match Move.promotion
      };
      container.appendChild(btn);
    });

    document.getElementById('promo-modal').classList.add('show');
  });
}

// ── Side selector ─────────────────────────────────────────────────────────────

function setSide(side) {
  state.humanSide = side;
  document.getElementById('btn-play-white').classList.toggle('active', side === 'white');
  document.getElementById('btn-play-black').classList.toggle('active', side === 'black');
  newGame();
}
