"""
renderer_web.py — FUTURE: web browser / multiplayer rendering layer for RETRIS.

This file is a stub. It will be implemented when the web portal is built.

=============================================================================
PLANNED ARCHITECTURE
=============================================================================

Platform split:
  render/renderer.py        — desktop (current PC layout, 460×600 canvas)
  render/renderer_mobile.py — Android full-screen layout (460×940 canvas)
  render/renderer_web.py    — THIS FILE — web portal layout (future)

Shared across all three:
  render/sprites.py         — block/ghost surface cache (get_block, get_ghost)
  render/game_over_anim.py  — per-block physics animation
  render/particles.py       — particle burst system
  logic/                    — game_logic, input_handler, touch_controls (unchanged)
  core/                     — game_state, app_state, board, piece (unchanged)

=============================================================================
WEB RENDERING APPROACH (planned)
=============================================================================

Two options under consideration:

Option A — Pygame WASM via Pygbag:
  - Compile main.py + full Python stack to WASM using Pygbag
  - Renderer runs unchanged in the browser via pygame-web
  - Pros: zero porting effort; cons: large payload (~20 MB), limited perf

Option B — JS canvas renderer (recommended for multiplayer):
  - Python game logic runs server-side (FastAPI / websockets)
  - Per-frame state serialised as JSON and pushed to browser clients
  - Browser receives: board grid, current piece, score, level, etc.
  - JS canvas renderer draws the state each frame
  - renderer_web.py becomes the Python side: state serialiser + websocket handler
  - Pros: real multiplayer, low latency; cons: requires JS renderer port

=============================================================================
MULTIPLAYER / ONLINE SCORING (planned features)
=============================================================================

  - Real-time 1v4 matches: send garbage lines on clears (like competitive Tetris)
  - Spectator mode: observe any active match
  - Online leaderboard: REST API backed by a lightweight DB (SQLite → Postgres)
  - Match rooms: create / join / invite
  - Hosted on a VPS or serverless platform (Fly.io / Railway / Render)

State the web server would expose:
  GET  /leaderboard             — top-N scores, JSON
  POST /score                   — submit a score (with auth token)
  WS   /match/{room_id}         — bidirectional game-state + garbage stream
  GET  /match/{room_id}/spectate — read-only state stream

=============================================================================
"""

raise NotImplementedError(
    "renderer_web.py is a future stub. "
    "The web portal has not been built yet."
)
