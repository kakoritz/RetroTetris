"""Integration tests for demo.py — catches import errors, API mismatches, and state logic."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import unittest
from unittest.mock import patch, MagicMock
import pygame

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
pygame.init()


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_gs_app():
    from game_state import GameState
    from app_state import AppState, MENU
    surf = pygame.Surface((460, 600))
    app = AppState(display=surf, screen=surf, current_scale=1.0)
    app.state = MENU
    gs = GameState()
    return gs, app


# ── Piece shape_name kwarg ────────────────────────────────────────────────────

def test_piece_shape_name_i():
    from piece import Piece
    p = Piece(shape_name='I')
    assert p.type == 'I'


def test_piece_shape_name_all_types():
    from piece import Piece
    from constants import SHAPES
    for name in SHAPES:
        p = Piece(shape_name=name)
        assert p.type == name
        assert p.shape


def test_piece_no_arg_still_random():
    from piece import Piece
    from constants import SHAPES
    p = Piece()
    assert p.type in SHAPES


# ── SCENARIOS structure ───────────────────────────────────────────────────────

def test_scenarios_count():
    from demo import SCENARIOS
    assert len(SCENARIOS) == 7


def test_scenarios_fields():
    from demo import SCENARIOS
    for label, board_factory, wait_ms in SCENARIOS:
        assert isinstance(label, str) and label
        for gap in (0, 5, 9):
            grid = board_factory(gap)
            assert len(grid) == 20
            assert all(len(row) == 10 for row in grid)
        assert wait_ms > 0


def test_board_gap_is_empty():
    """The gap column must be empty in every row that would be 'full'."""
    from demo import _board_1line
    for gap_col in range(10):
        grid = _board_1line(gap_col)
        assert grid[19][gap_col] == 0, f"gap_col={gap_col} should be empty in row 19"
        for col in range(10):
            if col != gap_col:
                assert grid[19][col] != 0, f"col {col} should be filled in row 19"


def test_vertical_i_fills_gap():
    """I piece at x=gap_col with _I_VERT_SHAPE fills exactly the gap column."""
    from demo import _I_VERT_SHAPE, _board_1line
    from board import Board
    from piece import Piece

    for gap_col in range(10):
        grid = _board_1line(gap_col)
        board = Board()
        for r in range(20):
            board.grid[r] = grid[r][:]

        p = Piece(shape_name='I')
        p.shape     = [row[:] for row in _I_VERT_SHAPE]
        p.rot_state = 1
        p.x         = gap_col
        p.y         = 0

        # Drop piece to the bottom
        while board.is_valid(p, dy=1):
            p.y += 1
        board.place(p)

        # Row 19 should now be fully filled
        assert all(board.grid[19]), f"gap_col={gap_col}: row 19 not full after drop"
        full = board.full_rows()
        assert 19 in full, f"gap_col={gap_col}: row 19 not detected as full"


# ── enter_demo ────────────────────────────────────────────────────────────────

@patch('music_game.start_sequence')
def test_enter_demo_sets_state(mock_start):
    from demo import enter_demo
    from app_state import DEMO
    gs, app = _make_gs_app()
    enter_demo(gs, app)
    assert app.state == DEMO
    assert app.demo_active is True
    assert app.demo_scenario_idx == 0
    assert app.demo_phase == 'setup'
    mock_start.assert_called_once()


# ── exit_demo ────────────────────────────────────────────────────────────────

@patch('music.start')
@patch('music_game.stop')
@patch('music_game.start_sequence')
def test_exit_demo_clears_active(mock_seq, mock_stop, mock_music_start):
    from demo import enter_demo, exit_demo
    from app_state import MENU
    gs, app = _make_gs_app()
    enter_demo(gs, app)
    exit_demo(gs, app)
    assert app.demo_active is False
    assert app.state == MENU
    mock_stop.assert_called_once()
    mock_music_start.assert_called_once()


# ── _load_scenario ────────────────────────────────────────────────────────────

@patch('music_game.start_sequence')
def test_load_scenario_positions_piece(mock_start):
    from demo import enter_demo, _load_scenario, _I_VERT_SHAPE, _I_VERT_ROT, SCENARIOS
    from app_state import DEMO
    gs, app = _make_gs_app()
    enter_demo(gs, app)

    for _ in range(20):   # run many times to exercise randomness
        _load_scenario(gs, app)
        assert gs.current.type == 'I'
        assert gs.current.rot_state == _I_VERT_ROT
        assert gs.current.shape == _I_VERT_SHAPE
        assert 0 <= gs.current.x <= 9
        assert app.state == DEMO
        assert app.demo_phase == 'fall'
        assert app.demo_scenario_wait_ms > 0


@patch('music_game.start_sequence')
def test_load_scenario_level_varies(mock_start):
    from demo import enter_demo, _load_scenario
    gs, app = _make_gs_app()
    enter_demo(gs, app)
    levels = set()
    for _ in range(50):
        _load_scenario(gs, app)
        levels.add(gs.level)
    assert len(levels) > 1, "level should vary across loads"


@patch('music_game.start_sequence')
def test_load_scenario_gap_varies(mock_start):
    from demo import enter_demo, _load_scenario
    gs, app = _make_gs_app()
    enter_demo(gs, app)
    xs = set()
    for _ in range(50):
        _load_scenario(gs, app)
        xs.add(gs.current.x)
    assert len(xs) > 1, "gap column (piece.x) should vary across loads"


# ── update_demo — setup phase transitions ─────────────────────────────────────

@patch('music_game.start_sequence')
def test_update_demo_setup_goes_to_fall(mock_start):
    from demo import enter_demo, update_demo
    from app_state import DEMO
    gs, app = _make_gs_app()
    enter_demo(gs, app)

    update_demo(gs, app, dt=16)
    assert app.demo_phase == 'fall'
    assert app.state == DEMO


# ── update_demo — fall phase gravity ─────────────────────────────────────────

@patch('music_game.start_sequence')
def test_fall_phase_moves_piece_down(mock_start):
    from demo import enter_demo, update_demo, _DEMO_FALL_INTERVAL
    from app_state import DEMO
    gs, app = _make_gs_app()
    enter_demo(gs, app)
    update_demo(gs, app, dt=16)   # setup → fall

    start_y = gs.current.y
    update_demo(gs, app, dt=_DEMO_FALL_INTERVAL + 1)
    assert gs.current.y > start_y or app.demo_phase == 'clearing'


# ── update_demo — wait phase advances scenario ────────────────────────────────

@patch('music_game.start_sequence')
def test_wait_phase_advances_on_timeout(mock_start):
    from demo import enter_demo, update_demo
    from app_state import DEMO
    gs, app = _make_gs_app()
    enter_demo(gs, app)

    app.demo_phase      = 'wait'
    app.demo_wait_timer = 10
    app.demo_scenario_idx = 2
    app.state = DEMO

    update_demo(gs, app, dt=20)
    assert app.demo_phase == 'setup'
    assert app.demo_scenario_idx == 3


# ── advance_scenario wraps around ────────────────────────────────────────────

def test_advance_scenario_wraps():
    from demo import _advance_scenario, SCENARIOS
    from app_state import AppState
    surf = pygame.Surface((460, 600))
    app = AppState(display=surf, screen=surf, current_scale=1.0)
    app.demo_scenario_idx = len(SCENARIOS) - 1
    from game_state import GameState
    gs = GameState()
    _advance_scenario(gs, app)
    assert app.demo_scenario_idx == 0


# ── score reset on start_new_game ─────────────────────────────────────────────

@patch('audio.play_spawn')
@patch('music_game.start_sequence')
def test_odometer_resets_on_new_game(mock_seq, mock_play):
    from demo import enter_demo
    from game_logic import start_new_game
    from app_state import PLAYING
    gs, app = _make_gs_app()
    enter_demo(gs, app)

    # Simulate score accumulated during demo
    app.score_disp        = 99999.0
    app.score_disp_digits = [9] * 8
    app.score_anim_offs   = [1.0] * 8

    start_new_game(gs, app)
    assert app.score_disp == 0.0
    assert app.score_disp_digits == [0] * 8
    assert app.score_anim_offs == [0.0] * 8
