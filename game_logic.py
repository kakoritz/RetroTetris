# game_logic.py — standalone game-logic helpers (extracted from main.py closures)
import pygame
import audio
import highscore
import music
import rotation
from piece import Piece
from constants import SHAPES, COLS, ROWS
from game_constants import (
    NEXT_FLASH_MS, GRAVITY_20G_LEVEL, LOCK_MAX_MOVES,
    PLACEMENT_SCORE, HD_FLASH_DURATION,
)
from game_state import GameState
from app_state import AppState, ENTER_NAME, GAME_OVER_ANIM, GAME_OVER, CLEARING


def spawn_next(gs: GameState, app: AppState) -> bool:
    gs.current         = gs.piece_queue.pop(0)
    gs.piece_queue.append(Piece())
    gs.next_flash_timer = NEXT_FLASH_MS
    gs.lock_timer       = 0
    gs.lock_move_count  = 0
    gs.hold_used        = False
    gs.last_action      = 'gravity'
    if gs.level >= GRAVITY_20G_LEVEL:
        while gs.board.is_valid(gs.current, dy=1):
            gs.current.y += 1
    audio.play_spawn(gs.current.color_id)
    return gs.board.is_valid(gs.current)


def do_hold(gs: GameState, app: AppState) -> None:
    if gs.hold_used:
        return
    gs.hold_used       = True
    gs.last_action     = 'gravity'
    gs.lock_timer      = gs.lock_move_count = 0

    gs.current.shape     = [row[:] for row in SHAPES[gs.current.type]]
    gs.current.rot_state = 0
    gs.current.x         = COLS // 2 - len(gs.current.shape[0]) // 2
    gs.current.y         = 0

    if gs.hold_piece is None:
        gs.hold_piece = gs.current
        gs.current    = gs.piece_queue.pop(0)
        gs.piece_queue.append(Piece())
        gs.next_flash_timer = NEXT_FLASH_MS
    else:
        gs.current, gs.hold_piece = gs.hold_piece, gs.current
        gs.current.shape     = [row[:] for row in SHAPES[gs.current.type]]
        gs.current.rot_state = 0
        gs.current.x         = COLS // 2 - len(gs.current.shape[0]) // 2
        gs.current.y         = 0

    if gs.level >= GRAVITY_20G_LEVEL:
        while gs.board.is_valid(gs.current, dy=1):
            gs.current.y += 1
    gs.last_action = 'gravity'
    audio.play_spawn(gs.current.color_id)


def start_new_game(gs: GameState, app: AppState) -> None:
    gs.reset()
    app.reset_das()
    audio.play_spawn(gs.current.color_id)


def end_game(gs: GameState, app: AppState) -> None:
    gs.stat_time = (pygame.time.get_ticks() - gs.stat_start_ms) / 1000.0
    music.fadeout(1200)
    app.go_anim.reset()
    if highscore.qualifies(gs.score):
        app.initials        = ['A', 'A', 'A']
        app.ini_cursor      = 0
        app.post_anim_state = ENTER_NAME
    else:
        app.post_anim_state = GAME_OVER
    app.state = GAME_OVER_ANIM


def reset_lock(gs: GameState) -> None:
    if not gs.board.is_valid(gs.current, dy=1) and gs.lock_move_count < LOCK_MAX_MOVES:
        gs.lock_timer = 0
        gs.lock_move_count += 1


def do_lock(gs: GameState, app: AppState) -> None:
    gs.tspin_type = rotation.detect_tspin(gs.board, gs.current, gs.last_action)
    gs.board.place(gs.current)
    gs.stat_pieces += 1
    audio.play('lock')
    app.reset_das()
    gs.lock_timer = gs.lock_move_count = 0
    gs.score     += PLACEMENT_SCORE
    gs.cascade_level      = 0
    gs.first_clear_tetris = False
    full = gs.board.full_rows()
    if full:
        full_set       = set(full)
        gs.wow_active  = all(
            all(c == 0 for c in gs.board.grid[r])
            for r in range(ROWS) if r not in full_set
        )
        gs.color_clear_id = None
        for row_i in full:
            row_colors = set(gs.board.grid[row_i][c] for c in range(COLS))
            if len(row_colors) == 1:
                gs.color_clear_id = next(iter(row_colors))
                break
        gs.clear_rows      = full_set
        gs.clear_count     = len(full)
        gs.clear_timer     = 0
        gs.clear_flash_idx = 0
        gs.clear_cells     = [
            (col, row_i, gs.board.grid[row_i][col])
            for row_i in full for col in range(COLS)
            if gs.board.grid[row_i][col]
        ]
        audio.play(gs.clear_count)
        app.state = CLEARING
    else:
        gs.combo = 0
        if not spawn_next(gs, app):
            end_game(gs, app)


def debug_clear_board(gs: GameState, app: AppState) -> None:
    for r in range(ROWS):
        for c in range(COLS):
            if gs.board.grid[r][c] == 0:
                gs.board.grid[r][c] = 1
    full_set          = set(range(ROWS))
    gs.wow_active     = True
    gs.clear_rows     = full_set
    gs.clear_count    = ROWS
    gs.clear_timer    = 0
    gs.clear_flash_idx = 0
    gs.clear_cells    = [
        (col, row_i, gs.board.grid[row_i][col])
        for row_i in range(ROWS) for col in range(COLS)
    ]
    gs.hd_flash_timer = HD_FLASH_DURATION
    audio.play(4)
    app.state = CLEARING
