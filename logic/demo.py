"""
demo.py — attract/demo mode for RETRIS.

Triggered by pressing D at the menu or after 60 s of menu idle.
Cycles through 7 pre-scripted scenarios, each loading a specific board
state and dropping a pre-positioned I piece into the gap to trigger the
event. Gap column and level theme are randomised per scenario so every
run looks different.

Exit: Space or Esc returns to the menu from any phase.
"""
import random
import pygame
from piece import Piece
from board import Board
from game_state import GameState
from app_state import AppState, MENU, CLEARING, CASCADING, DEMO
import music
import music_game


# ── tuning ────────────────────────────────────────────────────────────────────

_DEMO_FALL_INTERVAL = 320   # ms per one-row gravity step (slow enough to see)

# Pre-computed vertical I piece shape (1 CW rotation from the 1×4 spawn shape).
# Active column is at col_i=0, so board column = piece.x.
_I_VERT_SHAPE = [[1], [1], [1], [1]]
_I_VERT_ROT   = 1


# ── board helpers ─────────────────────────────────────────────────────────────

def _rows_with_gap(row_indices: list[int], gap_col: int,
                   color_cycle: list[int] | None = None) -> list[list[int]]:
    """20×10 grid: specified rows filled (cycling colors) except gap_col."""
    grid   = [[0] * 10 for _ in range(20)]
    colors = color_cycle or [2, 3, 5, 6, 7, 4, 2, 3, 5, 6]
    for ri in row_indices:
        for ci in range(10):
            if ci != gap_col:
                grid[ri][ci] = colors[ci % len(colors)]
    return grid


def _add_top_scatter(grid: list[list[int]], gap_col: int) -> None:
    """Scatter blocks in the upper board so a line clear never leaves an empty board."""
    other_cols = [c for c in range(10) if c != gap_col]
    for row in [2, 5, 9]:
        for c in random.sample(other_cols, random.randint(2, 4)):
            grid[row][c] = random.randint(2, 7)


# ── scenario board factories (each takes gap_col) ────────────────────────────

def _board_1line(gap_col: int)  -> list[list[int]]:
    grid = _rows_with_gap([19], gap_col)
    _add_top_scatter(grid, gap_col)
    return grid

def _board_2line(gap_col: int)  -> list[list[int]]:
    grid = _rows_with_gap([18, 19], gap_col)
    _add_top_scatter(grid, gap_col)
    return grid

def _board_3line(gap_col: int)  -> list[list[int]]:
    grid = _rows_with_gap([17, 18, 19], gap_col)
    _add_top_scatter(grid, gap_col)
    return grid

def _board_tetris(gap_col: int) -> list[list[int]]:
    grid = _rows_with_gap([16, 17, 18, 19], gap_col,
                          color_cycle=[3, 5, 6, 7, 4, 2, 3, 5, 6, 7])
    _add_top_scatter(grid, gap_col)
    return grid

def _board_color_clear(gap_col: int) -> list[list[int]]:
    grid = [[0] * 10 for _ in range(20)]
    # Trigger row: full cyan except gap (color clear fires when I fills it)
    for ci in range(10):
        if ci != gap_col:
            grid[19][ci] = 1
    # Scatter mixed+cyan above; gap_col must stay empty so the I piece reaches row 19
    for row in range(8, 19):
        density = 0.55 if row >= 14 else 0.28
        for ci in range(10):
            if ci != gap_col and random.random() < density:
                grid[row][ci] = 1 if random.random() < 0.32 else random.randint(2, 7)
    return grid

def _board_wow(gap_col: int) -> list[list[int]]:
    return _rows_with_gap([16, 17, 18, 19], gap_col,
                          color_cycle=[3, 5, 6, 7, 4, 2, 3, 5, 6, 7])

def _board_cascade(gap_col: int) -> list[list[int]]:
    grid = _rows_with_gap([17, 18, 19], gap_col)
    # Row 13 is a complete row that will float after rows 17-19 clear.
    for ci in range(10):
        grid[13][ci] = [2, 3, 5, 6, 7, 4, 2, 3, 5, 6][ci]
    return grid


# ── scenario definitions ──────────────────────────────────────────────────────
# Each entry: (label, board_factory(gap_col), wait_ms_after_clear)
# Gap column and level theme are randomised per load in _load_scenario.

SCENARIOS = [
    ("1× Line Clear",             _board_1line,       1400),
    ("2× Line Clear",             _board_2line,       1400),
    ("3× Line Clear",             _board_3line,       1500),
    ("RETRIS!  —  4× Line Clear", _board_tetris,      1800),
    ("COLOR CLEAR!",              _board_color_clear, 2000),
    ("BOARD CLEAR!  —  Perfect Clear", _board_wow,     2200),
    ("Full Cascade!",             _board_cascade,     2500),
]


# ── public API ────────────────────────────────────────────────────────────────

def enter_demo(gs: GameState, app: AppState) -> None:
    """Switch to DEMO state and queue the first scenario."""
    app.state              = DEMO
    app.demo_active        = True
    app.demo_scenario_idx  = 0
    app.demo_phase         = 'setup'
    app.demo_fall_timer    = 0
    app.menu_idle_timer    = 0
    music_game.start_sequence()


def exit_demo(gs: GameState, app: AppState) -> None:
    """Return to the menu from any demo phase."""
    app.demo_active = False
    app.demo_phase  = 'setup'
    app.state       = MENU
    music_game.stop()
    music.start()


def _load_scenario(gs: GameState, app: AppState) -> None:
    """Initialise gs for the current demo scenario with randomised gap + level."""
    idx          = app.demo_scenario_idx % len(SCENARIOS)
    label, board_factory, wait_ms = SCENARIOS[idx]

    gap_col      = random.randint(0, 9)
    level        = random.randint(1, 10)

    app.demo_label            = label
    app.demo_scenario_wait_ms = wait_ms

    gs.reset()
    gs.level      = level
    gs.speed_tier = 1   # keep the clear animations at base speed

    grid = board_factory(gap_col)
    for r in range(20):
        gs.board.grid[r] = grid[r][:]

    # Pre-position vertical I piece above the gap column.
    # Vertical I shape = [[1],[1],[1],[1]]; active board col = piece.x + 0 = piece.x.
    gs.current           = Piece(shape_name='I')
    gs.current.shape     = [row[:] for row in _I_VERT_SHAPE]
    gs.current.rot_state = _I_VERT_ROT
    gs.current.x         = gap_col
    gs.current.y         = 0
    gs.piece_queue       = [Piece(shape_name='I') for _ in range(5)]

    app.state           = DEMO
    app.demo_phase      = 'fall'
    app.demo_fall_timer = 0


def _advance_scenario(gs: GameState, app: AppState) -> None:
    app.demo_scenario_idx = (app.demo_scenario_idx + 1) % len(SCENARIOS)
    app.demo_phase        = 'setup'
    app.demo_fall_timer   = 0


def update_demo(gs: GameState, app: AppState, dt: int) -> None:
    """Called every frame while app.demo_active is True.

    Phases:
      'setup'    — load scenario board and position piece
      'fall'     — piece falls at demo speed; on landing, do_lock fires
      'clearing' — wait for CLEARING / CASCADING to finish in the main loop
      'wait'     — hold on the cleared board, then advance
    """
    # Score is meaningless in demo — keep it and the odometer frozen at zero.
    gs.score              = 0
    app.score_disp        = 0.0
    app.score_disp_digits = [0] * 8
    app.score_anim_offs   = [0.0] * 8

    if app.demo_phase == 'setup':
        _load_scenario(gs, app)
        return

    if app.demo_phase == 'fall':
        # If state changed away from DEMO, do_lock already ran (e.g. CLEARING).
        if app.state != DEMO:
            app.demo_phase = 'clearing'
            return

        app.demo_fall_timer += dt
        if app.demo_fall_timer < _DEMO_FALL_INTERVAL:
            return
        app.demo_fall_timer -= _DEMO_FALL_INTERVAL

        if gs.board.is_valid(gs.current, dy=1):
            gs.current.y += 1
        else:
            # Piece has landed — lock it and let CLEARING/CASCADING run.
            import audio
            from game_logic import do_lock
            audio.play('hard_drop')
            do_lock(gs, app)
            app.demo_phase = 'clearing'
            # do_lock changed app.state to CLEARING (or PLAYING if no full rows)
        return

    if app.demo_phase == 'clearing':
        if app.state in (CLEARING, CASCADING):
            return   # let tick_clearing / tick_cascading run normally
        # PLAYING means the clear chain is done and a new piece was spawned.
        # Push that piece off-screen and enter the wait phase.
        gs.current.y  = -20
        app.state     = DEMO
        app.demo_phase      = 'wait'
        app.demo_wait_timer = app.demo_scenario_wait_ms
        return

    if app.demo_phase == 'wait':
        app.demo_wait_timer -= dt
        if app.demo_wait_timer <= 0:
            _advance_scenario(gs, app)
