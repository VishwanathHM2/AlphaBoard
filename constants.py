"""
constants.py - Chess engine constants and configuration.

Defines piece values, board indices, castling flags, and piece-square tables.
"""

# ──────────────────────────────────────────────
# Piece symbols
# ──────────────────────────────────────────────
WHITE_PIECES = set("PNBRQK")
BLACK_PIECES = set("pnbrqk")
EMPTY = "."

# Side identifiers
WHITE = "white"
BLACK = "black"

# ──────────────────────────────────────────────
# Material values (centipawns)
# ──────────────────────────────────────────────
PIECE_VALUES = {
    "P": 100,  "p": 100,
    "N": 320,  "n": 320,
    "B": 330,  "b": 330,
    "R": 500,  "r": 500,
    "Q": 900,  "q": 900,
    "K": 20000,"k": 20000,
    ".": 0,
}

# ──────────────────────────────────────────────
# Castling right flags (bitmask)
# ──────────────────────────────────────────────
CASTLE_WK = 1   # White kingside
CASTLE_WQ = 2   # White queenside
CASTLE_BK = 4   # Black kingside
CASTLE_BQ = 8   # Black queenside

# ──────────────────────────────────────────────
# Board geometry helpers
# ──────────────────────────────────────────────
# Files a-h → 0-7; ranks 1-8 → row 0-7 (row 0 = rank 1 / White's back rank)
def sq(file: int, rank: int) -> int:
    """Convert (file 0-7, rank 0-7) to board index 0-63."""
    return rank * 8 + file

def file_of(index: int) -> int:
    return index % 8

def rank_of(index: int) -> int:
    return index // 8

# ──────────────────────────────────────────────
# Piece-square tables (from White's perspective, rank 8 first)
# Indexed [0..63] where index 0 = a8 ... index 63 = h1
# We store them rank-8-first so they read naturally in code.
# ──────────────────────────────────────────────

# Pawns – encourage centre advance and passed pawn potential
PST_P = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
]

PST_N = [
   -50,-40,-30,-30,-30,-30,-40,-50,
   -40,-20,  0,  0,  0,  0,-20,-40,
   -30,  0, 10, 15, 15, 10,  0,-30,
   -30,  5, 15, 20, 20, 15,  5,-30,
   -30,  0, 15, 20, 20, 15,  0,-30,
   -30,  5, 10, 15, 15, 10,  5,-30,
   -40,-20,  0,  5,  5,  0,-20,-40,
   -50,-40,-30,-30,-30,-30,-40,-50,
]

PST_B = [
   -20,-10,-10,-10,-10,-10,-10,-20,
   -10,  0,  0,  0,  0,  0,  0,-10,
   -10,  0,  5, 10, 10,  5,  0,-10,
   -10,  5,  5, 10, 10,  5,  5,-10,
   -10,  0, 10, 10, 10, 10,  0,-10,
   -10, 10, 10, 10, 10, 10, 10,-10,
   -10,  5,  0,  0,  0,  0,  5,-10,
   -20,-10,-10,-10,-10,-10,-10,-20,
]

PST_R = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
]

PST_Q = [
   -20,-10,-10, -5, -5,-10,-10,-20,
   -10,  0,  0,  0,  0,  0,  0,-10,
   -10,  0,  5,  5,  5,  5,  0,-10,
    -5,  0,  5,  5,  5,  5,  0, -5,
     0,  0,  5,  5,  5,  5,  0, -5,
   -10,  5,  5,  5,  5,  5,  0,-10,
   -10,  0,  5,  0,  0,  0,  0,-10,
   -20,-10,-10, -5, -5,-10,-10,-20,
]

PST_K_MG = [
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -20,-30,-30,-40,-40,-30,-30,-20,
   -10,-20,-20,-20,-20,-20,-20,-10,
    20, 20,  0,  0,  0,  0, 20, 20,
    20, 30, 10,  0,  0, 10, 30, 20,
]

# Maps piece char → PST (White's perspective, rank-8-first)
WHITE_PST = {
    "P": PST_P,
    "N": PST_N,
    "B": PST_B,
    "R": PST_R,
    "Q": PST_Q,
    "K": PST_K_MG,
}

# Infinity placeholder for search
INF = 1_000_000
