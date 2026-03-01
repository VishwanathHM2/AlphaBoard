# AlphaBoard
A playable chess engine built from scratch in Python. Features full legal move generation, alpha-beta pruning with iterative deepening, and quiescence search. Comes with both a browser-based UI (Flask) and a command-line interface. No external chess libraries -everything from move generation to evaluation is hand-written and documented.


AlphaBoard
A fully functional chess engine built in Python, playable via a web browser or command line.
The engine uses alpha-beta pruning with iterative deepening and quiescence search to find strong moves without exploring every possible position. Piece evaluation combines material values with piece-square tables and a mobility bonus, giving the engine a sense of positional play beyond just counting pieces.
How It Works
The engine searches the game tree to a configurable depth (2–5 plies), pruning branches that cannot affect the final result. At leaf nodes, quiescence search extends the calculation through captures only, preventing the engine from making moves that look good but walk into an immediate recapture. Move ordering (captures first, ranked by MVV-LVA) ensures the most promising branches are explored first, maximising the effectiveness of pruning.
Features

Legal move generation for all piece types including castling, en passant, and promotion
Alpha-beta pruning with iterative deepening
Quiescence search to avoid the horizon effect
Material + piece-square table + mobility evaluation
Flask web interface with a clean dark-themed board
Full move history, captured pieces tracker, and undo support
Playable as White or Black against the engine
Also playable via CLI with no dependencies beyond Python

Running
bashpip install flask
cd AlphaBoard
python server.py
# Open http://localhost:5000
Or via the command line:
bashcd chess_engine
python main.py
```

Project Structure
```
AlphaBoard/
├── server.py           Flask API server
├── board.py            Board state and move execution
├── move.py             Move representation
├── move_generator.py   Legal move generation
├── search.py           Alpha-beta, quiescence, iterative deepening
├── evaluation.py       Position evaluation function
├── constants.py        Piece values, piece-square tables
├── utils.py            Perft testing and move parsing
├── main.py             CLI interface
├── templates/
│   └── index.html      Web UI template
└── static/
    ├── css/            Board and UI stylesheets
    └── js/             API client, board renderer, game logic
