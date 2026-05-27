"""
demo.py — attract/demo mode for T3TR1S.

Triggered by pressing D at the menu or after 60 s of menu idle.
Cycles through pre-scripted scenarios that showcase every major game event.
Each scenario loads a specific board state and uses a simple bot to place
pieces at target positions so the event fires reliably.

Exit: Space or Esc returns to the menu.
"""
import copy
import pygame
from piece import Piece
from board import Board
from game_state import GameState
from app_state import AppState, MENU, PLAYING, CLEARING, CASCADING, DEMO
import music
import music_game


# ── board helpers ─────────────────────────────────────────────────────────────

def _rows_with_gap(row_indices: list[int], gap_col: int,
                   color_cycle: list[int] | None = None) -> list[list[int]]:
    """20×10 grid: specified rows filled (cycling colors) except gap_col."""
    grid = [[0] * 10 for _ in range(20)]
    colors = color_cycle or [2, 3, 5, 6, 7, 4, 2, 3, 5, 6]
    for ri in row_indices:
        for ci in range(10):
            if ci != gap_col:
                grid[ri][ci] = colors[ci % len(colors)]
    return grid


def _monochrome_row(row_idx: int, color_id: int, gap_col: int) -> list[list[int]]:
    """Single mono-color row (for color-clear demo)."""
    grid = [[0] * 10 for _ in range(20)]
    for ci in range(10):
        if ci != gap_col:
            grid[row_idx][ci] = color_id
    return grid


def _cascade_board() -> list[list[int]]:
    """Board with 3 clearable rows + a floating complete row above."""
    grid = _rows_with_gap([17, 18, 19], gap_col=9)
    # Row 13 is a complete row that will float after rows 17-19 clear.
    for ci in range(10):
        grid[13][ci] = [2, 3, 5, 6, 7, 4, 2, 3, 5, 6][ci]
    return grid


def _wow_board() -> list[list[int]]:
    """4 rows filled except col 9 — dropping I vertical clears all → WOW."""
    return _rows_with_gap([16, 17, 18, 19], gap_col=9,
                           color_cycle=[3, 5, 6, 7, 4, 2, 3, 5, 6, 7])


def _color_clear_board() -> list[list[int]]:
    """Row 19 all cyan (color_id=1) except col 9."""
    return _monochrome_row(19, color_id=1, gap_col=9)


# ── scenario definitions ──────────────────────────────────────────────────────
# Each entry: (label, grid_factory, piece_name, target_x, target_rot, wait_ms)
# The bot rotates the piece to target_rot then slides to target_x and hard-drops.

_I_VERTICAL_ROT = 1   # I piece rotation state for vertical orientation
_I_VERTICAL_X   = 8   # piece.x so col-1-of-shape lands on board col 9

SCENARIOS = [
    ("1× Line Clear",
     lambda: _rows_with_gap([19],               gap_col=9), 'I', _I_VERTICAL_X, _I_VERTICAL_ROT, 2800),
    ("2× Line Clear",
     lambda: _rows_with_gap([18, 19],            gap_col=9), 'I', _I_VERTICAL_X, _I_VERTICAL_ROT, 2800),
    ("3× Line Clear",
     lambda: _rows_with_gap([17, 18, 19],        gap_col=9), 'I', _I_VERTICAL_X, _I_VERTICAL_ROT, 3000),
    ("TETRIS!  —  4× Line Clear",
     lambda: _rows_with_gap([16, 17, 18, 19],    gap_col=9), 'I', _I_VERTICAL_X, _I_VERTICAL_ROT, 3500),
    ("COLOR CLEAR!",
     _color_clear_board,                                      'I', _I_VERTICAL_X, _I_VERTICAL_ROT, 3800),
    ("WOW!  —  Perfect Clear",
     _wow_board,                                              'I', _I_VERTICAL_X, _I_VERTICAL_ROT, 4000),
    ("Full Cascade!",
     _cascade_board,                                          'I', _I_VERTICAL_X, _I_VERTICAL_ROT, 4500),
]


# ── public API ────────────────────────────────────────────────────────────────

def enter_demo(gs: GameState, app: AppState) -> None:
    """Switch to DEMO state and set up the first scenario."""
    app.state              = DEMO
    app.demo_scenario_idx  = 0
    app.demo_phase         = 'setup'
    app.demo_bot_timer     = 0
    app.menu_idle_timer    = 0
    music_game.start_sequence()   # restart game music from tier 1


def _load_scenario(gs: GameState, app: AppState) -> None:
    """Initialise gs for the current demo scenario."""
    idx  = app.demo_scenario_idx % len(SCENARIOS)
    label, board_fn, piece_name, target_x, target_rot, _ = SCENARIOS[idx]

    app.demo_label      = label
    app.demo_target_col = target_x
    app.demo_target_rot = target_rot

    gs.reset()
    # Replace the board grid with the scenario's preset
    grid = board_fn()
    for r in range(20):
        gs.board.grid[r] = grid[r][:]

    # Force the current piece to the required shape
    gs.current      = Piece(shape_name=piece_name)
    gs.current.x    = 3   # start near middle; bot will move it
    gs.current.y    = 0
    gs.piece_queue  = [Piece() for _ in range(5)]
    app.state = DEMO   # ensure we stay in demo (gs.reset triggers PLAYING internally)


def _advance_scenario(gs: GameState, app: AppState) -> None:
    app.demo_scenario_idx = (app.demo_scenario_idx + 1) % len(SCENARIOS)
    app.demo_phase = 'setup'
    app.demo_bot_timer = 0


_BOT_MOVE_INTERVAL = 90   # ms between bot moves


def update_demo(gs: GameState, app: AppState, dt: int) -> None:
    """Called every frame while app.state == DEMO."""

    if app.demo_phase == 'setup':
        _load_scenario(gs, app)
        app.demo_phase     = 'move'
        app.demo_bot_timer = 0
        return

    if app.demo_phase == 'wait':
        app.demo_wait_timer -= dt
        if app.demo_wait_timer <= 0:
            _advance_scenario(gs, app)
        return

    # 'move' phase — the bot acts on gs.current while the game is DEMO/PLAYING
    if app.state not in (DEMO, PLAYING, CLEARING, CASCADING):
        # Piece locked and game ended — restart with next scenario
        _advance_scenario(gs, app)
        return

    # If CLEARING or CASCADING, let the physics run; check when back to DEMO
    if app.state in (CLEARING, CASCADING):
        return

    # Physics: gravity is handled by main.py for PLAYING, so demo keeps PLAYING
    # override state to PLAYING so gravity runs
    if app.state == DEMO:
        from app_state import PLAYING as _PLAYING
        app.state = _PLAYING

    # Bot move timer
    app.demo_bot_timer -= dt
    if app.demo_bot_timer > 0:
        return
    app.demo_bot_timer = _BOT_MOVE_INTERVAL

    cur  = gs.current
    trot = app.demo_target_rot
    tx   = app.demo_target_col

    # Rotate toward target
    if cur.rot_state != trot:
        _bot_rotate_cw(gs)
        return

    # Slide toward target x
    if cur.x < tx:
        _bot_move(gs, +1)
        return
    if cur.x > tx:
        _bot_move(gs, -1)
        return

    # Aligned — hard drop
    from game_logic import do_lock
    while gs.board.is_valid(cur, dy=1):
        cur.y += 1
    import audio
    audio.play('hard_drop')
    do_lock(gs, app)

    # After lock, wait for clearing/cascading to settle, then wait
    app.demo_phase      = 'wait'
    app.demo_wait_timer = SCENARIOS[app.demo_scenario_idx % len(SCENARIOS)][5]
    app.state = DEMO   # release back to DEMO so the wait phase runs


def _bot_rotate_cw(gs: GameState) -> None:
    from rotation import try_rotate
    try_rotate(gs.board, gs.current, *gs.current.rotated_cw())


def _bot_move(gs: GameState, dx: int) -> None:
    if gs.board.is_valid(gs.current, dx=dx):
        gs.current.x += dx
