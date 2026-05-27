# tests/test_game_logic.py — integration tests for game_logic.py
#
# These tests verify that the closures extracted from main.py into
# game_logic.py behave identically to their original inline forms.
# audio / music calls are patched so no mixer is required.

import pygame
import pytest
from unittest.mock import patch, MagicMock

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Minimal pygame init without display or mixer
pygame.init()

from board import Board
from piece import Piece
from game_state import GameState
from app_state import AppState, PLAYING, CLEARING, GAME_OVER_ANIM, ENTER_NAME, GAME_OVER
from game_constants import NEXT_FLASH_MS, LOCK_MAX_MOVES, PLACEMENT_SCORE, HD_FLASH_DURATION
from game_logic import spawn_next, do_hold, start_new_game, end_game, reset_lock, do_lock, debug_clear_board


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_gs():
    gs = GameState()
    gs.reset()
    return gs


def _make_app():
    surf = pygame.Surface((460, 600))
    return AppState(surf, surf, 1.0)


# ── spawn_next ────────────────────────────────────────────────────────────────

@patch("audio.play_spawn")
def test_spawn_next_queue_length_stable(mock_spawn):
    gs, app = _make_gs(), _make_app()
    initial_len = len(gs.piece_queue)
    spawn_next(gs, app)
    assert len(gs.piece_queue) == initial_len, \
        "spawn_next must keep piece_queue the same length"


@patch("audio.play_spawn")
def test_spawn_next_resets_lock_state(mock_spawn):
    gs, app = _make_gs(), _make_app()
    gs.lock_timer      = 999
    gs.lock_move_count = 5
    gs.hold_used       = True
    spawn_next(gs, app)
    assert gs.lock_timer      == 0
    assert gs.lock_move_count == 0
    assert gs.hold_used       is False


@patch("audio.play_spawn")
def test_spawn_next_sets_next_flash_timer(mock_spawn):
    gs, app = _make_gs(), _make_app()
    gs.next_flash_timer = 0
    spawn_next(gs, app)
    assert gs.next_flash_timer == NEXT_FLASH_MS


@patch("audio.play_spawn")
def test_spawn_next_returns_true_for_valid_spawn(mock_spawn):
    gs, app = _make_gs(), _make_app()
    result = spawn_next(gs, app)
    assert result is True


@patch("audio.play_spawn")
def test_spawn_next_returns_false_when_blocked(mock_spawn):
    gs, app = _make_gs(), _make_app()
    # Fill top rows so spawn position is blocked
    from constants import COLS
    for c in range(COLS):
        gs.board.grid[0][c] = 1
        gs.board.grid[1][c] = 1
    result = spawn_next(gs, app)
    assert result is False


# ── do_hold ───────────────────────────────────────────────────────────────────

@patch("audio.play_spawn")
def test_do_hold_first_hold_stores_piece(mock_spawn):
    gs, app = _make_gs(), _make_app()
    assert gs.hold_piece is None
    original_type = gs.current.type
    do_hold(gs, app)
    assert gs.hold_piece is not None
    assert gs.hold_piece.type == original_type
    assert gs.hold_used is True


@patch("audio.play_spawn")
def test_do_hold_idempotent_when_used(mock_spawn):
    gs, app = _make_gs(), _make_app()
    do_hold(gs, app)
    piece_after_first = gs.current.type
    do_hold(gs, app)  # should be a no-op
    assert gs.current.type == piece_after_first, \
        "second hold in same piece must be a no-op"


@patch("audio.play_spawn")
def test_do_hold_swap_restores_piece(mock_spawn):
    gs, app = _make_gs(), _make_app()
    first_type = gs.current.type
    do_hold(gs, app)
    second_type = gs.current.type
    # Reset hold_used so we can swap back
    gs.hold_used = False
    do_hold(gs, app)
    assert gs.current.type == first_type
    assert gs.hold_piece.type == second_type


@patch("audio.play_spawn")
def test_do_hold_resets_piece_to_spawn_position(mock_spawn):
    gs, app = _make_gs(), _make_app()
    # Move piece so it's not at spawn position
    gs.current.x = 0; gs.current.y = 5
    do_hold(gs, app)
    # The held piece was reset; get it back
    gs.hold_used = False
    do_hold(gs, app)
    assert gs.current.y == 0, "swapped-in piece must be at spawn row"


# ── start_new_game ────────────────────────────────────────────────────────────

@patch("audio.play_spawn")
def test_start_new_game_resets_score(mock_spawn):
    gs, app = _make_gs(), _make_app()
    gs.score = 9999
    start_new_game(gs, app)
    assert gs.score == 0


@patch("audio.play_spawn")
def test_start_new_game_resets_board(mock_spawn):
    gs, app = _make_gs(), _make_app()
    from constants import COLS, ROWS
    for r in range(ROWS):
        for c in range(COLS):
            gs.board.grid[r][c] = 1
    start_new_game(gs, app)
    assert all(gs.board.grid[r][c] == 0 for r in range(ROWS) for c in range(COLS))


@patch("audio.play_spawn")
def test_start_new_game_resets_das(mock_spawn):
    gs, app = _make_gs(), _make_app()
    app.das_dir     = 1
    app.das_timer   = 500
    app.das_charged = True
    app.keys_held.add(pygame.K_RIGHT)
    start_new_game(gs, app)
    assert app.das_dir     == 0
    assert app.das_timer   == 0
    assert app.das_charged is False
    assert len(app.keys_held) == 0


# ── reset_lock ────────────────────────────────────────────────────────────────

@patch("audio.play_spawn")
def test_reset_lock_only_fires_when_grounded(mock_spawn):
    gs, app = _make_gs(), _make_app()
    # Not grounded — piece is far from bottom
    gs.current.y    = 0
    gs.lock_timer   = 999
    gs.lock_move_count = 0
    reset_lock(gs)
    assert gs.lock_timer == 999, "reset_lock must not fire when piece is not grounded"


@patch("audio.play_spawn")
def test_reset_lock_fires_when_grounded(mock_spawn):
    gs, app = _make_gs(), _make_app()
    # Ground the piece by dropping it to the floor
    while gs.board.is_valid(gs.current, dy=1):
        gs.current.y += 1
    gs.lock_timer      = 999
    gs.lock_move_count = 0
    reset_lock(gs)
    assert gs.lock_timer == 0


@patch("audio.play_spawn")
def test_reset_lock_respects_max_moves(mock_spawn):
    gs, app = _make_gs(), _make_app()
    while gs.board.is_valid(gs.current, dy=1):
        gs.current.y += 1
    gs.lock_timer      = 999
    gs.lock_move_count = LOCK_MAX_MOVES
    reset_lock(gs)
    assert gs.lock_timer == 999, "reset_lock must not fire after LOCK_MAX_MOVES"


# ── do_lock ───────────────────────────────────────────────────────────────────

@patch("audio.play")
@patch("audio.play_spawn")
def test_do_lock_no_clear_spawns_next(mock_spawn, mock_play):
    gs, app = _make_gs(), _make_app()
    # Drop piece to the floor so the top spawn area stays clear
    while gs.board.is_valid(gs.current, dy=1):
        gs.current.y += 1
    app.state = PLAYING
    do_lock(gs, app)
    assert app.state == PLAYING, "no-clear lock must stay in PLAYING"


@patch("audio.play")
@patch("audio.play_spawn")
def test_do_lock_adds_placement_score(mock_spawn, mock_play):
    gs, app = _make_gs(), _make_app()
    gs.score = 0
    do_lock(gs, app)
    assert gs.score >= PLACEMENT_SCORE


@patch("audio.play")
@patch("audio.play_spawn")
def test_do_lock_clear_sets_clearing_state(mock_spawn, mock_play):
    gs, app = _make_gs(), _make_app()
    from constants import COLS, ROWS
    # Fill bottom 4 rows so a clear fires when piece locks
    for r in range(ROWS - 4, ROWS):
        for c in range(COLS):
            gs.board.grid[r][c] = 1
    # Put current piece somewhere it can lock without overlapping filled rows
    gs.current.y = 0
    app.state = PLAYING
    do_lock(gs, app)
    assert app.state == CLEARING


@patch("audio.play")
@patch("audio.play_spawn")
def test_do_lock_increments_stat_pieces(mock_spawn, mock_play):
    gs, app = _make_gs(), _make_app()
    gs.stat_pieces = 0
    do_lock(gs, app)
    assert gs.stat_pieces == 1


# ── debug_clear_board ─────────────────────────────────────────────────────────

@patch("audio.play")
def test_debug_clear_board_sets_clearing_state(mock_play):
    gs, app = _make_gs(), _make_app()
    app.state = PLAYING
    debug_clear_board(gs, app)
    assert app.state == CLEARING


@patch("audio.play")
def test_debug_clear_board_sets_wow_active(mock_play):
    gs, app = _make_gs(), _make_app()
    debug_clear_board(gs, app)
    assert gs.wow_active is True


@patch("audio.play")
def test_debug_clear_board_sets_hd_flash(mock_play):
    gs, app = _make_gs(), _make_app()
    debug_clear_board(gs, app)
    assert gs.hd_flash_timer == HD_FLASH_DURATION


@patch("audio.play")
def test_debug_clear_board_fills_all_rows(mock_play):
    from constants import COLS, ROWS
    gs, app = _make_gs(), _make_app()
    debug_clear_board(gs, app)
    from constants import ROWS
    assert gs.clear_count == ROWS
    assert len(gs.clear_rows) == ROWS


# ── end_game ──────────────────────────────────────────────────────────────────

@patch("music.fadeout")
@patch("highscore.qualifies", return_value=False)
def test_end_game_non_qualifying_sets_game_over(mock_qualifies, mock_fadeout):
    gs, app = _make_gs(), _make_app()
    app.state = PLAYING
    end_game(gs, app)
    assert app.state == GAME_OVER_ANIM
    assert app.post_anim_state == GAME_OVER


@patch("music.fadeout")
@patch("highscore.qualifies", return_value=True)
def test_end_game_qualifying_sets_enter_name(mock_qualifies, mock_fadeout):
    gs, app = _make_gs(), _make_app()
    end_game(gs, app)
    assert app.state == GAME_OVER_ANIM
    assert app.post_anim_state == ENTER_NAME


@patch("music.fadeout")
@patch("highscore.qualifies", return_value=True)
def test_end_game_resets_initials(mock_qualifies, mock_fadeout):
    gs, app = _make_gs(), _make_app()
    app.initials   = ['Z', 'Z', 'Z']
    app.ini_cursor = 2
    end_game(gs, app)
    assert app.initials   == ['A', 'A', 'A']
    assert app.ini_cursor == 0


@patch("music.fadeout")
@patch("highscore.qualifies", return_value=False)
def test_end_game_records_stat_time(mock_qualifies, mock_fadeout):
    gs, app = _make_gs(), _make_app()
    gs.stat_start_ms = pygame.time.get_ticks() - 5000  # pretend 5 s elapsed
    end_game(gs, app)
    assert gs.stat_time >= 4.0  # at least ~5 s


# ── GameState.reset sanity ────────────────────────────────────────────────────

def test_game_state_reset_queue_length():
    gs = _make_gs()
    assert len(gs.piece_queue) == 5, "queue must start at 5 pieces"


def test_game_state_reset_next_flash_timer_zero():
    gs = _make_gs()
    assert gs.next_flash_timer == 0, "no flash on initial board"


def test_game_state_spawn_preserves_queue_length():
    gs, app = _make_gs(), _make_app()
    with patch("audio.play_spawn"):
        for _ in range(10):
            spawn_next(gs, app)
    assert len(gs.piece_queue) == 5
