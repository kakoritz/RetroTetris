import colorsys
import math
import random
import pygame
import sys

import audio
audio.pre_init()

import config
import highscore
import music
import music_game
from game_over_anim import GameOverAnim
from particles import spawn as spawn_particles
from particles import update as update_particles
from particles import draw as draw_particles
from constants import (
    COLS, ROWS, CELL_SIZE,
    BOARD_WIDTH, BOARD_HEIGHT, SIDEBAR_WIDTH, SCREEN_WIDTH, SCREEN_HEIGHT,
    FPS, BG_COLOR, GRID_COLOR, BORDER_COLOR, WHITE, YELLOW,
    COLORS, SHAPES, SCORE_TABLE, fall_speed,
)
from board import Board
from piece import Piece
from sprites import get_block, get_ghost
import rotation
import renderer
from renderer import (
    _font, _BOARD_LINE,
    draw_board, _draw_danger_line, draw_piece, draw_ghost,
    draw_popup, draw_sidebar, draw_game_over_overlay,
    draw_settings, draw_pause, draw_music_test,
    draw_menu, draw_name_entry, draw_leaderboard,
)
from game_constants import (
    DAS_DELAY, DAS_REPEAT,
    LOCK_DELAY, LOCK_MAX_MOVES,
    FLASH_MS, FLASH_TOTAL, FLASH_COLOR_NORM, FLASH_COLOR_QUAD,
    FLASH_MS_WOW, FLASH_TOTAL_WOW,
    WOW_BONUS, WOW_POPUP_DURATION, COLOR_CLEAR_BONUS,
    TSPIN_SCORES, TSPIN_MINI_SCORES,
    COMBO_BONUS_UNIT,
    GRAVITY_20G_LEVEL,
    PLACEMENT_SCORE,
    SPEED_RESET_INTERVAL, CASCADE_INTERVAL_GROWTH,
    PALETTE_PHASE_INTERVAL,
    PAGE_VOL_STEP,
    SPEED_RESET_FLASH_DURATION,
    CASCADE_STEP_MS, CASCADE_BONUS_PER_RESET,
    POPUP_DURATION, SHAKE_DURATION, SHAKE_INTENSITY, HD_FLASH_DURATION,
    POPUP_STYLES,
)


# ── states ────────────────────────────────────────────────────────────────────
MENU        = "menu"
PLAYING     = "playing"
CLEARING    = "clearing"
GAME_OVER   = "game_over"
ENTER_NAME  = "enter_name"
LEADERBOARD = "leaderboard"
SETTINGS       = "settings"
GAME_OVER_ANIM = "game_over_anim"
PAUSED         = "paused"
MUSIC_TEST     = "music_test"
CASCADING      = "cascading"   # animated full-board gravity (full cascade mode)

_MUSIC_END = pygame.USEREVENT + 1   # fired by mixer when a track finishes naturally

_INITIALS_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ "

# ── board / piece drawing (implementations in renderer.py) ───────────────────


# ── game helper ───────────────────────────────────────────────────────────────

def new_game():
    return Board(), Piece(), [Piece() for _ in range(5)], 0, 0, 1, 0


# ── main loop ─────────────────────────────────────────────────────────────────

def _make_display(scale: float) -> pygame.Surface:
    w = int(SCREEN_WIDTH  * scale)
    h = int(SCREEN_HEIGHT * scale)
    return pygame.display.set_mode((w, h))


def _build_icon() -> pygame.Surface:
    """32×32 window icon: T-piece (stem pointing up) in T-piece purple.

    Layout (each X = one cell, cs=10px):
        . X .
        X X X
    Rendered with the same NES bevel style used for in-game blocks.
    """
    color = (160, 0, 240)
    cs    = 10
    surf  = pygame.Surface((32, 32), pygame.SRCALPHA)
    ox, oy = 1, 6   # centres the 30×20 piece in the 32×32 canvas
    hi  = tuple(min(c + 90, 255) for c in color)
    sh  = tuple(max(c - 80,   0) for c in color)
    for cx, cy in [(1, 0), (0, 1), (1, 1), (2, 1)]:
        x = ox + cx * cs
        y = oy + cy * cs
        pygame.draw.rect(surf, (*color, 255),    (x, y, cs, cs))
        pygame.draw.rect(surf, (8, 8, 20, 255),  (x, y, cs, cs), 1)
        pygame.draw.line(surf, (*hi, 255), (x+1, y+1),    (x+cs-2, y+1))
        pygame.draw.line(surf, (*hi, 255), (x+1, y+1),    (x+1, y+cs-2))
        pygame.draw.line(surf, (*sh, 255), (x+2, y+cs-2), (x+cs-2, y+cs-2))
        pygame.draw.line(surf, (*sh, 255), (x+cs-2, y+2), (x+cs-2, y+cs-2))
    return surf


def main():
    pygame.init()
    pygame.mixer.music.set_endevent(_MUSIC_END)

    # Icon must be set before set_mode so the OS picks it up on window creation.
    pygame.display.set_icon(_build_icon())

    current_scale = config.get_scale()
    display = _make_display(current_scale)

    if pygame.display.get_driver() == "offscreen":
        print(
            "\nT3TR1S: display unavailable — SDL fell back to offscreen mode.\n"
            "This usually means the X server has run out of client connections\n"
            "(common when VS Code, Firefox, and Discord are all open).\n"
            "Close a few heavy apps and try again.\n"
        )
        pygame.quit()
        sys.exit(1)

    # Logical surface: everything renders here at the native 460×600 size
    screen  = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    pygame.display.set_caption("T3TR1S")
    clock = pygame.time.Clock()
    music.start()

    audio.prime()   # pre-build SFX so volume slider takes effect immediately

    state = MENU
    board, current, piece_queue, score, lines, level, fall_timer = new_game()
    best  = highscore.best()

    # settings
    music_vol_pct    = 40                          # 0-100
    sfx_vol_pct      = 100                         # 0-100
    ghost_opacity_pct = config.get_ghost_opacity() # 0-100, persisted
    settings_row          = 0                      # 0=music 1=sfx 2=scale 3=ghost
    settings_return_state = MENU                   # MENU or PAUSED

    # game-over animation
    go_anim         = GameOverAnim()
    post_anim_state = GAME_OVER   # ENTER_NAME or GAME_OVER after animation

    # line-clear animation
    clear_rows:      set   = set()
    clear_count:     int   = 0
    clear_timer:     int   = 0
    clear_flash_idx: int   = 0

    # DAS
    das_dir:     int  = 0
    das_timer:   int  = 0
    das_charged: bool = False
    keys_held:   set  = set()

    # popup
    popup_count: int = 0
    popup_timer: int = 0

    # next-piece box flash (brief white outline when piece changes)
    next_flash_timer: int = 0
    NEXT_FLASH_MS = 220

    # name entry
    initials   = ['A', 'A', 'A']
    ini_cursor = 0

    # leaderboard
    lb_scores   = []
    lb_hi_name  = None
    lb_hi_score = None

    blink_timer    = 0
    blink_on       = True
    pre_pause_vol  = 0.0
    music_test_tier = 1

    particles:      list = []
    shake_timer:    int  = 0
    hd_flash_timer: int  = 0
    clear_cells:    list = []
    danger:         bool = False   # True when any block occupies the top-10 rows
    wow_active:     bool = False   # True during a perfect-clear (board-empty) event
    # Each entry: {'x', 'y', 'vy', 'timer', 'max_timer'}
    # Spawned when rows above the danger line are cleared; float upward and fade.
    danger_bonuses: list = []
    score_deltas:   list = []
    _cheat_seq:     list = []   # tracks 3→2→1 debug sequence; never exposed in docs

    # lock delay
    lock_timer:      int  = 0    # counts up while piece is grounded
    lock_move_count: int  = 0    # resets used this piece; caps at LOCK_MAX_MOVES

    # hold piece
    hold_piece:      object = None   # Piece or None
    hold_used:       bool   = False  # True after hold is used; resets on piece lock

    # T-spin / back-to-back / combo
    last_action: str       = 'gravity'  # 'rotate','move','soft_drop','hard_drop','gravity'
    tspin_type:  str|None  = None       # 'full', 'mini', or None — detected at lock time
    btb_active:  bool      = False      # True when last difficult clear enables B2B
    combo:       int       = 0          # consecutive clears; 0 = no bonus yet
    # Floating "COMBO ×N" labels drawn on the board (same system as danger_bonuses)
    combo_labels: list     = []

    # speed tier + reset system
    speed_tier:       int   = 1                      # drives fall speed; resets every SPEED_RESET_INTERVAL pts
    next_speed_reset: int   = SPEED_RESET_INTERVAL   # score threshold for next reset
    speed_reset_count: int  = 0                      # total resets so far this game
    reset_bonus_mult: float = 1.0                    # +0.1 per reset; multiplies line-clear scores

    # full board cascade mode: toggled on/off by each speed reset
    full_cascade_mode: bool = False

    # cascade gravity (per clear chain)
    cascade_level:      int  = 0     # 0 = initial clear; 1+ = cascade passes
    first_clear_tetris: bool = False  # True if the initial lock clear was 4 lines

    # speed-reset overlay
    speed_reset_flash_timer: int = 0

    # full cascade animation
    cascade_anim_timer: int = 0

    # color-clear detection: set in _do_lock when a cleared row is mono-color
    color_clear_id: int | None = None

    # level-up flash (sidebar level value briefly turns white)
    level_up_flash_timer: int = 0

    # per-game statistics (shown on game-over screen)
    stat_pieces:   int   = 0
    stat_tetrises: int   = 0
    stat_tspins:   int   = 0
    stat_combo:    int   = 0   # longest combo streak reached this game
    stat_start_ms: int   = pygame.time.get_ticks()
    stat_time:     float = 0.0   # seconds, set in _end_game

    # DAS / ARR — loaded from config, adjustable in settings
    _das_preset            = config.get_das_preset()
    das_delay:  int = config.DAS_SETTINGS[_das_preset][0]
    das_repeat: int = config.DAS_SETTINGS[_das_preset][1]
    das_preset: str = _das_preset

    def _spawn_next():
        nonlocal current, piece_queue, lock_timer, lock_move_count, hold_used
        nonlocal last_action, next_flash_timer
        current = piece_queue.pop(0)
        piece_queue.append(Piece())
        next_flash_timer = NEXT_FLASH_MS
        lock_timer       = 0
        lock_move_count  = 0
        hold_used        = False
        last_action      = 'gravity'
        # 20G: immediately drop new piece to the floor on spawn.
        if level >= GRAVITY_20G_LEVEL:
            while board.is_valid(current, dy=1):
                current.y += 1
        audio.play_spawn(current.color_id)
        return board.is_valid(current)

    def _do_hold():
        """Swap current piece into the hold slot (or take from hold if occupied).

        The held piece is reset to its spawn orientation and position.
        Hold is locked for the rest of the current piece's life — one hold per piece.
        """
        nonlocal current, piece_queue, hold_piece, hold_used
        nonlocal lock_timer, lock_move_count, last_action, next_flash_timer
        if hold_used:
            return
        hold_used   = True
        last_action = 'gravity'
        lock_timer  = lock_move_count = 0

        # Reset current to spawn state before stashing it.
        from constants import SHAPES, COLS as _COLS
        current.shape     = [row[:] for row in SHAPES[current.type]]
        current.rot_state = 0
        current.x         = _COLS // 2 - len(current.shape[0]) // 2
        current.y         = 0

        if hold_piece is None:
            hold_piece = current
            current    = piece_queue.pop(0)
            piece_queue.append(Piece())
            next_flash_timer = NEXT_FLASH_MS
        else:
            current, hold_piece = hold_piece, current
            # Reset swapped-in piece to spawn position
            current.shape     = [row[:] for row in SHAPES[current.type]]
            current.rot_state = 0
            current.x         = _COLS // 2 - len(current.shape[0]) // 2
            current.y         = 0

        # 20G: floor the swapped-in piece immediately.
        if level >= GRAVITY_20G_LEVEL:
            while board.is_valid(current, dy=1):
                current.y += 1
        last_action = 'gravity'
        audio.play_spawn(current.color_id)

    def _start_new_game():
        nonlocal board, current, piece_queue, score, lines, level, fall_timer
        nonlocal hold_piece, hold_used, lock_timer, lock_move_count
        nonlocal popup_count, popup_timer, wow_active
        nonlocal last_action, tspin_type, btb_active, combo, combo_labels
        nonlocal speed_tier, next_speed_reset, speed_reset_count, reset_bonus_mult
        nonlocal full_cascade_mode, cascade_level, first_clear_tetris
        nonlocal speed_reset_flash_timer, danger_bonuses, score_deltas, next_flash_timer
        nonlocal color_clear_id, level_up_flash_timer
        nonlocal stat_pieces, stat_tetrises, stat_tspins, stat_combo, stat_start_ms, stat_time
        board, current, piece_queue, score, lines, level, fall_timer = new_game()
        hold_piece   = None
        hold_used    = False
        lock_timer   = lock_move_count = 0
        popup_count  = popup_timer = 0
        wow_active   = False
        last_action  = 'gravity'
        tspin_type   = None
        btb_active   = False
        combo        = 0
        combo_labels = []
        speed_tier          = 1
        next_speed_reset    = SPEED_RESET_INTERVAL
        speed_reset_count   = 0
        reset_bonus_mult    = 1.0
        full_cascade_mode   = False
        cascade_level       = 0
        first_clear_tetris  = False
        speed_reset_flash_timer = 0
        next_flash_timer = 0
        danger_bonuses = []
        score_deltas   = []
        color_clear_id       = None
        level_up_flash_timer = 0
        stat_pieces  = stat_tetrises = stat_tspins = stat_combo = 0
        stat_time    = 0.0
        stat_start_ms = pygame.time.get_ticks()
        _reset_das()
        audio.play_spawn(current.color_id)

    def _end_game():
        nonlocal state, initials, ini_cursor, post_anim_state, stat_time
        stat_time = (pygame.time.get_ticks() - stat_start_ms) / 1000.0
        music.fadeout(1200)
        go_anim.reset()
        if highscore.qualifies(score):
            initials        = ['A', 'A', 'A']
            ini_cursor      = 0
            post_anim_state = ENTER_NAME
        else:
            post_anim_state = GAME_OVER
        state = GAME_OVER_ANIM

    def _reset_das():
        nonlocal das_dir, das_timer, das_charged
        das_dir = 0; das_timer = 0; das_charged = False; keys_held.clear()

    def _reset_lock():
        """Reset the lock-delay clock after a successful move or rotate.

        Only resets if the piece is currently grounded AND we have moves left.
        Once LOCK_MAX_MOVES resets are used the piece locks on the next tick
        regardless — this prevents a player from stalling indefinitely.
        """
        nonlocal lock_timer, lock_move_count
        if not board.is_valid(current, dy=1) and lock_move_count < LOCK_MAX_MOVES:
            lock_timer = 0
            lock_move_count += 1

    def _do_lock():
        """Place the current piece, check for clears, spawn the next piece."""
        nonlocal state, lock_timer, lock_move_count
        nonlocal clear_rows, clear_count, clear_timer, clear_flash_idx
        nonlocal clear_cells, wow_active, tspin_type, combo
        nonlocal score, cascade_level, first_clear_tetris
        nonlocal color_clear_id, stat_pieces
        # Detect T-spin BEFORE placing — piece position + last_action must be current.
        tspin_type = rotation.detect_tspin(board, current, last_action)
        board.place(current)
        stat_pieces += 1
        audio.play('lock')
        _reset_das()
        lock_timer = lock_move_count = 0
        score += PLACEMENT_SCORE   # tiny reward for every piece locked
        cascade_level = 0
        first_clear_tetris = False
        full = board.full_rows()
        if full:
            full_set        = set(full)
            wow_active      = all(
                all(c == 0 for c in board.grid[r])
                for r in range(ROWS) if r not in full_set
            )
            # Color-clear detection: any cleared row where all 10 cells share one color
            color_clear_id = None
            for row_i in full:
                row_colors = set(board.grid[row_i][c] for c in range(COLS))
                if len(row_colors) == 1:
                    color_clear_id = next(iter(row_colors))
                    break
            clear_rows      = full_set
            clear_count     = len(full)
            clear_timer     = 0
            clear_flash_idx = 0
            clear_cells     = [
                (col, row_i, board.grid[row_i][col])
                for row_i in full for col in range(COLS)
                if board.grid[row_i][col]
            ]
            audio.play(clear_count)
            state = CLEARING
        else:
            combo = 0   # piece placed without clearing — streak broken
            if not _spawn_next():
                _end_game()

    def _debug_clear_board():
        """Fill every row solid then hand off to the normal CLEARING path so
        the WOW event fires exactly as it would in real play."""
        nonlocal clear_rows, clear_count, clear_timer, clear_flash_idx
        nonlocal clear_cells, wow_active, state, hd_flash_timer
        for r in range(ROWS):
            for c in range(COLS):
                if board.grid[r][c] == 0:
                    board.grid[r][c] = 1  # colour 1 — any non-zero value clears
        full_set        = set(range(ROWS))
        wow_active      = True             # board will be empty after the clear
        clear_rows      = full_set
        clear_count     = ROWS             # 20-line "clear" — uses WOW flash path
        clear_timer     = 0
        clear_flash_idx = 0
        clear_cells     = [
            (col, row_i, board.grid[row_i][col])
            for row_i in range(ROWS) for col in range(COLS)
        ]
        hd_flash_timer  = HD_FLASH_DURATION
        audio.play(4)                      # Tetris clear sound — closest available
        state           = CLEARING

    while True:
        dt = clock.tick(FPS)

        blink_timer += dt
        if blink_timer >= 500:
            blink_timer = 0
            blink_on    = not blink_on

        # ── events ────────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            # Music track finished — advance sequence.
            # After on_music_end() the new track resets its volume to _game_vol,
            # so we must re-apply the 90 % reduction if we're still paused.
            if (event.type == _MUSIC_END
                    and state in (PLAYING, CLEARING, CASCADING, PAUSED)):
                music_game.on_music_end()
                if state == PAUSED:
                    pygame.mixer.music.set_volume(pre_pause_vol * 0.10)

            # KEYUP: track DAS key releases regardless of state
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    keys_held.discard(pygame.K_LEFT)
                    if das_dir == -1:
                        das_dir = (1 if pygame.K_RIGHT in keys_held else 0)
                        das_timer = 0; das_charged = False
                elif event.key == pygame.K_RIGHT:
                    keys_held.discard(pygame.K_RIGHT)
                    if das_dir == 1:
                        das_dir = (-1 if pygame.K_LEFT in keys_held else 0)
                        das_timer = 0; das_charged = False

            if event.type != pygame.KEYDOWN:
                continue

            # ── global keys (any state) ───────────────────────────────────────
            if event.key == pygame.K_m:
                music.toggle_mute()
                music_game.set_muted(music.is_muted())
                continue

            if event.key == pygame.K_PAGEUP:
                music_vol_pct = min(100, music_vol_pct + PAGE_VOL_STEP)
                music.set_volume(music_vol_pct / 100)
                music_game.set_volume(music_vol_pct / 100)
                continue

            if event.key == pygame.K_PAGEDOWN:
                music_vol_pct = max(0, music_vol_pct - PAGE_VOL_STEP)
                music.set_volume(music_vol_pct / 100)
                music_game.set_volume(music_vol_pct / 100)
                continue

            # ── MENU ──────────────────────────────────────────────────────────
            if state == MENU:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    _start_new_game()
                    best = highscore.best()
                    music.fadeout(400)
                    music_game.start_sequence()
                    state = PLAYING
                elif event.key == pygame.K_s:
                    settings_row          = 0
                    settings_return_state = MENU
                    state = SETTINGS
                elif event.key == pygame.K_t:
                    music_test_tier = 1
                    music.fadeout(300)
                    music_game.start_level(music_test_tier)
                    state = MUSIC_TEST

            # ── PLAYING ───────────────────────────────────────────────────────
            elif state == PLAYING:
                # Secret 3-2-1 debug sequence: triggers a full board clear + WOW.
                _CHEAT = [pygame.K_3, pygame.K_2, pygame.K_1]
                if event.key == _CHEAT[len(_cheat_seq)]:
                    _cheat_seq.append(event.key)
                    if len(_cheat_seq) == 3:
                        _cheat_seq.clear()
                        _debug_clear_board()
                        continue
                else:
                    # Any key that doesn't advance the sequence (including a wrong
                    # digit) resets it, so the user must press 3-2-1 cleanly.
                    _cheat_seq.clear()

                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    pre_pause_vol = pygame.mixer.music.get_volume()
                    pygame.mixer.music.set_volume(max(0.0, pre_pause_vol * 0.10))
                    state = PAUSED
                elif event.key == pygame.K_LEFT:
                    keys_held.add(pygame.K_LEFT)
                    das_dir = -1; das_timer = 0; das_charged = False
                    if board.is_valid(current, dx=-1):
                        current.x -= 1
                        last_action = 'move'
                        audio.play('move')
                        _reset_lock()
                        if level >= GRAVITY_20G_LEVEL:
                            while board.is_valid(current, dy=1):
                                current.y += 1
                elif event.key == pygame.K_RIGHT:
                    keys_held.add(pygame.K_RIGHT)
                    das_dir = 1; das_timer = 0; das_charged = False
                    if board.is_valid(current, dx=1):
                        current.x += 1
                        last_action = 'move'
                        audio.play('move')
                        _reset_lock()
                        if level >= GRAVITY_20G_LEVEL:
                            while board.is_valid(current, dy=1):
                                current.y += 1
                elif event.key == pygame.K_DOWN:
                    if board.is_valid(current, dy=1):
                        current.y += 1
                        score      += 1   # +1 per row soft-dropped
                        last_action = 'soft_drop'
                        lock_timer  = 0
                elif event.key == pygame.K_UP:
                    if event.mod & pygame.KMOD_CTRL:
                        if rotation.try_rotate(board, current, *current.rotated_ccw()):
                            last_action = 'rotate'
                            _reset_lock()
                    else:
                        if rotation.try_rotate(board, current, *current.rotated_cw()):
                            last_action = 'rotate'
                            _reset_lock()
                elif event.key == pygame.K_z:
                    if rotation.try_rotate(board, current, *current.rotated_ccw()):
                        last_action = 'rotate'
                        _reset_lock()
                elif event.key == pygame.K_c:
                    _do_hold()
                elif event.key == pygame.K_SPACE:
                    # Hard drop: instant commitment — no lock delay.
                    hd_flash_timer = HD_FLASH_DURATION
                    _hd_start_y = current.y
                    while board.is_valid(current, dy=1):
                        current.y += 1
                    score += (current.y - _hd_start_y) * 2   # +2 per row hard-dropped
                    last_action = 'hard_drop'
                    audio.play('hard_drop')
                    fall_timer  = 0
                    _do_lock()

            # ── GAME OVER ANIM (press any key to continue) ────────────────────
            elif state == GAME_OVER_ANIM:
                if go_anim.all_landed:
                    state = post_anim_state

            # ── PAUSED ────────────────────────────────────────────────────────
            # Only Space resumes — Q exits, everything else is ignored.
            # This prevents Alt+Tab, window events, or accidental keypresses
            # from resuming mid-game.
            elif state == PAUSED:
                if event.key == pygame.K_q:
                    music_game.stop()
                    music.start_menu()
                    state = MENU
                elif event.key == pygame.K_SPACE:
                    pygame.mixer.music.set_volume(pre_pause_vol)
                    state = PLAYING
                elif event.key == pygame.K_s:
                    # Restore full volume so volume adjustments in settings are audible
                    pygame.mixer.music.set_volume(pre_pause_vol)
                    settings_row          = 0
                    settings_return_state = PAUSED
                    state = SETTINGS
                # all other keys silently ignored while paused

            # ── GAME OVER ─────────────────────────────────────────────────────
            elif state == GAME_OVER:
                if event.key == pygame.K_r:
                    _start_new_game()
                    music_game.stop()
                    music_game.start_sequence()
                    state = PLAYING
                elif event.key in (pygame.K_SPACE, pygame.K_ESCAPE):
                    music_game.stop()
                    music.start_menu()
                    state = MENU
                elif event.key == pygame.K_l:
                    lb_scores   = highscore.load()
                    lb_hi_name  = lb_hi_score = None
                    state       = LEADERBOARD

            # ── ENTER NAME ────────────────────────────────────────────────────
            elif state == ENTER_NAME:
                idx = _INITIALS_CHARS
                if event.key == pygame.K_UP:
                    pos = (idx.index(initials[ini_cursor]) - 1) % len(idx)
                    initials[ini_cursor] = idx[pos]
                elif event.key == pygame.K_DOWN:
                    pos = (idx.index(initials[ini_cursor]) + 1) % len(idx)
                    initials[ini_cursor] = idx[pos]
                elif event.key == pygame.K_LEFT and ini_cursor > 0:
                    ini_cursor -= 1
                elif event.key in (pygame.K_RIGHT, pygame.K_RETURN, pygame.K_KP_ENTER):
                    if ini_cursor < 2:
                        ini_cursor += 1
                    else:
                        name        = ''.join(initials).strip() or "???"
                        lb_scores   = highscore.insert(name, score, lines, level)
                        lb_hi_name  = name
                        lb_hi_score = score
                        best        = highscore.best()
                        state       = LEADERBOARD
                elif pygame.K_a <= event.key <= pygame.K_z:
                    initials[ini_cursor] = chr(event.key).upper()
                    if ini_cursor < 2:
                        ini_cursor += 1

            # ── LEADERBOARD ───────────────────────────────────────────────────
            elif state == LEADERBOARD:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                    music_game.stop()
                    music.start_menu()
                    state = MENU
                elif event.key == pygame.K_r:
                    _start_new_game()
                    music_game.stop()
                    music_game.start_sequence()
                    state = PLAYING

            # ── MUSIC PREVIEW ─────────────────────────────────────────────────
            elif state == MUSIC_TEST:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN,
                                 pygame.K_KP_ENTER):
                    music_game.stop()
                    music.start_menu()
                    state = MENU
                elif event.key == pygame.K_UP:
                    music_test_tier = max(1, music_test_tier - 1)
                    music_game.start_level(music_test_tier)
                elif event.key == pygame.K_DOWN:
                    music_test_tier = min(10, music_test_tier + 1)
                    music_game.start_level(music_test_tier)

            # ── SETTINGS ──────────────────────────────────────────────────────
            elif state == SETTINGS:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                    if settings_return_state == PAUSED:
                        # Re-apply pause volume (user may have changed music_vol_pct)
                        pre_pause_vol = music_vol_pct / 100
                        pygame.mixer.music.set_volume(max(0.0, pre_pause_vol * 0.10))
                        state = PAUSED
                    else:
                        state = MENU
                elif event.key == pygame.K_UP:
                    settings_row = (settings_row - 1) % 5
                elif event.key == pygame.K_DOWN:
                    settings_row = (settings_row + 1) % 5
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    delta = -5 if event.key == pygame.K_LEFT else 5
                    if settings_row == 0:
                        music_vol_pct = max(0, min(100, music_vol_pct + delta))
                        music.set_volume(music_vol_pct / 100)
                        music_game.set_volume(music_vol_pct / 100)
                    elif settings_row == 1:
                        sfx_vol_pct = max(0, min(100, sfx_vol_pct + delta))
                        audio.set_sfx_volume(sfx_vol_pct / 100)
                        audio.play('rotate')   # instant SFX preview
                    elif settings_row == 2:
                        scales = config.VALID_SCALES
                        idx = scales.index(current_scale) if current_scale in scales else 0
                        idx = max(0, min(len(scales) - 1,
                                        idx + (1 if event.key == pygame.K_RIGHT else -1)))
                        new_scale = scales[idx]
                        if new_scale != current_scale:
                            current_scale = new_scale
                            config.set_scale(current_scale)
                            display = _make_display(current_scale)
                    elif settings_row == 3:
                        ghost_opacity_pct = max(0, min(100, ghost_opacity_pct + delta))
                        config.set_ghost_opacity(ghost_opacity_pct)
                    else:   # row 4 — DAS / ARR preset
                        presets = config.VALID_DAS_PRESETS
                        idx = presets.index(das_preset) if das_preset in presets else 1
                        idx = max(0, min(len(presets) - 1,
                                        idx + (1 if event.key == pygame.K_RIGHT else -1)))
                        das_preset  = presets[idx]
                        das_delay, das_repeat = config.DAS_SETTINGS[das_preset]
                        config.set_das_preset(das_preset)

        # ── DAS auto-repeat ───────────────────────────────────────────────────
        if state == PLAYING and das_dir != 0:
            das_timer += dt
            if not das_charged:
                if das_timer >= das_delay:
                    das_charged = True
                    das_timer   = 0
            else:
                if das_repeat == 0:
                    # Instant ARR — one move per frame while key held
                    if board.is_valid(current, dx=das_dir):
                        current.x += das_dir
                        last_action = 'move'
                        audio.play('move')
                        _reset_lock()
                        if level >= GRAVITY_20G_LEVEL:
                            while board.is_valid(current, dy=1):
                                current.y += 1
                else:
                    while das_timer >= das_repeat:
                        das_timer -= das_repeat
                        if board.is_valid(current, dx=das_dir):
                            current.x += das_dir
                            last_action = 'move'
                            audio.play('move')
                            _reset_lock()
                            if level >= GRAVITY_20G_LEVEL:
                                while board.is_valid(current, dy=1):
                                    current.y += 1

        # ── danger detection → tier-1 tension music + warning line ──────────
        # Row indices 0-9 are the top half of the board.  Any filled cell there
        # triggers tension mode; clearing back below row 10 releases it.
        if state in (PLAYING, CLEARING, CASCADING):
            danger = any(any(row) for row in board.grid[:10])
            music_game.set_danger(danger)

        # ── gravity + lock delay ─────────────────────────────────────────────
        if state == PLAYING:
            grounded = not board.is_valid(current, dy=1)

            fall_timer += dt
            if fall_timer >= fall_speed(speed_tier):
                fall_timer = 0
                if not grounded:
                    if level >= GRAVITY_20G_LEVEL:
                        # 20G: drop all the way to the floor on each gravity tick.
                        while board.is_valid(current, dy=1):
                            current.y += 1
                    else:
                        current.y  += 1
                        lock_timer  = 0   # reset lock clock on natural descent
                    last_action = 'gravity'

            # Lock delay: count up while grounded; expire → lock the piece.
            grounded = not board.is_valid(current, dy=1)   # re-check after drop
            if grounded:
                lock_timer += dt
                if lock_timer >= LOCK_DELAY:
                    _do_lock()

        # ── line-clear animation ──────────────────────────────────────────────
        elif state == CLEARING:
            clear_timer += dt
            # WOW (perfect clear) gets a longer, faster rainbow flash.
            fms   = FLASH_MS_WOW    if wow_active else FLASH_MS.get(clear_count, 80)
            ftotal = FLASH_TOTAL_WOW if wow_active else FLASH_TOTAL.get(clear_count, 2)
            if clear_timer >= fms:
                clear_timer -= fms
                clear_flash_idx += 1
                if clear_flash_idx >= ftotal:
                    # ── scoring ───────────────────────────────────────────────
                    lines += clear_count

                    # Danger-zone multiplier: any cleared row above row 10 → 2×.
                    danger_rows = [r for r in clear_rows if r < 10]
                    danger_mult = 2 if danger_rows else 1

                    # Cascade multiplier: 1× for the first clear, 2× for first
                    # cascade, 3× for second, etc.
                    cascade_mult = min(cascade_level + 1, 4)

                    # Base line-clear score: T-spin tables override SCORE_TABLE.
                    is_tspin      = tspin_type is not None and not wow_active
                    is_difficult  = (clear_count == 4 or is_tspin) and not wow_active
                    if is_tspin:
                        tbl        = TSPIN_MINI_SCORES if tspin_type == 'mini' else TSPIN_SCORES
                        base_score = tbl.get(clear_count, 0) * (level + 1)
                    else:
                        base_score = SCORE_TABLE.get(clear_count, 0) * (level + 1)

                    # Tetris×Tetris: first clear was a Tetris AND this cascade
                    # is also a Tetris — override cascade mult to 4×.
                    tetris_x_tetris = (cascade_level == 1
                                       and clear_count == 4
                                       and first_clear_tetris)
                    if tetris_x_tetris:
                        cascade_mult = 4

                    # Back-to-back: 1.5× on consecutive difficult clears.
                    btb_bonus = is_difficult and btb_active
                    if btb_bonus:
                        base_score = int(base_score * 1.5)

                    clear_delta = int(base_score * cascade_mult * danger_mult * reset_bonus_mult)
                    score += clear_delta

                    # Floating score-delta label centred on board
                    if clear_delta > 0:
                        if is_tspin and btb_bonus:
                            _dcol = (220, 130, 255)
                        elif is_tspin:
                            _dcol = (200, 100, 255)
                        elif btb_bonus:
                            _dcol = (255, 215, 0)
                        elif cascade_level > 0:
                            _dcol = (80, 255, 180)
                        elif danger_mult == 2:
                            _dcol = (255, 140, 0)
                        else:
                            _dcol = (220, 220, 255)
                        score_deltas.append({
                            'text':      f"+{clear_delta:,}",
                            'color':     _dcol,
                            'x':         float(BOARD_WIDTH * 0.68),
                            'y':         float(BOARD_HEIGHT * 0.52),
                            'vy':        -70.0,
                            'timer':     1600,
                            'max_timer': 1600,
                        })

                    # Combo bonus: 50 × combo count × (level + 1); combo = 0 on
                    # first clear in a row (no bonus yet), increments each clear.
                    combo_bonus = COMBO_BONUS_UNIT * combo * (level + 1)
                    score      += combo_bonus
                    if combo >= 1:   # spawn label when there's an actual bonus
                        combo_labels.append({
                            'text':      f"COMBO ×{combo + 1}",
                            'x':         float(BOARD_WIDTH // 2 - 32),
                            'y':         float(BOARD_HEIGHT // 2),
                            'vy':        -90.0,
                            'timer':     1400,
                            'max_timer': 1400,
                        })
                    combo += 1
                    stat_combo = max(stat_combo, combo)

                    # Stats: count Tetrises and T-spins
                    if clear_count == 4:
                        stat_tetrises += 1
                    if is_tspin:
                        stat_tspins += 1

                    if wow_active:
                        score += WOW_BONUS * (level + 1)

                    # Update B2B state for next clear.
                    if is_difficult:
                        btb_active = True
                    elif not wow_active and clear_count > 0:
                        btb_active = False   # non-difficult clear breaks the chain

                    # Spawn a floating ×2 label for each danger-zone row cleared.
                    for r in danger_rows:
                        danger_bonuses.append({
                            'x':         float(random.randint(10, BOARD_WIDTH - 50)),
                            'y':         float(r * CELL_SIZE),
                            'vy':        -115.0,
                            'timer':     1300,
                            'max_timer': 1300,
                        })

                    # Track level and speed tier.
                    old_level = level
                    level     = lines // 10 + 1
                    if level > old_level:
                        speed_tier = min(speed_tier + (level - old_level), 20)
                        level_up_flash_timer = 700   # sidebar level value flashes white
                        if old_level < GRAVITY_20G_LEVEL <= level:
                            popup_count = 14
                            popup_timer = int(POPUP_DURATION * 1.5)

                    # Speed reset: every SPEED_RESET_INTERVAL points fall speed
                    # drops back to tier 1, the score multiplier rises by 0.1,
                    # and Full Cascade Mode toggles on/off.
                    speed_reset_triggered = False
                    while score >= next_speed_reset:
                        next_speed_reset     += SPEED_RESET_INTERVAL + speed_reset_count * CASCADE_INTERVAL_GROWTH
                        speed_tier            = 1
                        speed_reset_count    += 1
                        reset_bonus_mult      = round(1.0 + speed_reset_count * 0.1, 1)
                        full_cascade_mode     = not full_cascade_mode
                        speed_reset_triggered = True
                    if speed_reset_triggered:
                        speed_reset_flash_timer = SPEED_RESET_FLASH_DURATION

                    best  = max(best, score)

                    # Track whether this (first) clear was a Tetris so that a
                    # cascade Tetris can trigger the T×T event.
                    if cascade_level == 0:
                        first_clear_tetris = (clear_count == 4)

                    # ── clear lines ───────────────────────────────────────────
                    board.clear_lines()

                    # ── color clear: blast every remaining cell of that color ──
                    _had_color_clear = False
                    if color_clear_id is not None:
                        cc_removed = board.remove_color(color_clear_id)
                        color_clear_id = None
                        if cc_removed:
                            particles      += spawn_particles(cc_removed, 4)
                            score          += COLOR_CLEAR_BONUS
                            best            = max(best, score)
                            _had_color_clear = True

                    # ── visual feedback for THIS clear pass ───────────────────
                    big_clear = (wow_active or clear_count == 4
                                 or (is_tspin and clear_count == 3)
                                 or tetris_x_tetris)
                    particles += spawn_particles(clear_cells, clear_count)
                    if big_clear:
                        shake_timer = SHAKE_DURATION

                    # ── popup selection ───────────────────────────────────────
                    # Priority: WOW > COLOR CLEAR > T×T > T-spin/B2B > cascade > normal
                    if wow_active:
                        popup_count = 0
                        popup_timer = WOW_POPUP_DURATION
                        wow_active  = False
                    elif _had_color_clear:
                        popup_count = 15
                        popup_timer = WOW_POPUP_DURATION
                    elif tetris_x_tetris:
                        popup_count = 13   # "TETRIS×TETRIS!" — board-centred
                        popup_timer = WOW_POPUP_DURATION
                    elif is_tspin and btb_bonus:
                        popup_count = 8   # "B2B T-SPIN!"
                        popup_timer = POPUP_DURATION
                    elif is_tspin and tspin_type == 'full':
                        popup_count = 5   # "T-SPIN!"
                        popup_timer = POPUP_DURATION
                    elif is_tspin:
                        popup_count = 6   # "T-SPIN MINI"
                        popup_timer = POPUP_DURATION
                    elif btb_bonus and clear_count == 4:
                        popup_count = 7   # "B2B TETRIS!"
                        popup_timer = POPUP_DURATION
                    elif cascade_level >= 4:
                        popup_count = 12   # "INSANE!"
                        popup_timer = POPUP_DURATION
                    elif cascade_level == 3:
                        popup_count = 11   # "Crazy!"
                        popup_timer = POPUP_DURATION
                    elif cascade_level == 2:
                        popup_count = 10   # "Woah!"
                        popup_timer = POPUP_DURATION
                    elif cascade_level == 1:
                        popup_count = 9    # "Wild!"
                        popup_timer = POPUP_DURATION
                    else:
                        popup_count = clear_count
                        popup_timer = POPUP_DURATION

                    tspin_type = None   # consumed

                    # ── cascade check ─────────────────────────────────────────
                    # Normal mode: only completely isolated singleton blocks fall.
                    # Full Cascade Mode (active after each odd speed reset):
                    #   every block with empty space below it falls — the
                    #   "Full Board Cascade Effect."
                    if full_cascade_mode:
                        # Animated domino fall — hand off to CASCADING state.
                        cascade_anim_timer = 0
                        state = CASCADING
                    else:
                        # Normal mode: all floating blocks fall instantly (same physics
                        # as full cascade, just no animation or scoring bonus).
                        board.settle_blocks()
                        cascade_rows = board.full_rows()
                        if cascade_rows:
                            cascade_level  += 1
                            full_set        = set(cascade_rows)
                            wow_active      = all(
                                all(c == 0 for c in board.grid[r])
                                for r in range(ROWS) if r not in full_set
                            )
                            clear_rows      = full_set
                            clear_count     = len(cascade_rows)
                            clear_timer     = 0
                            clear_flash_idx = 0
                            clear_cells     = [
                                (col, row_i, board.grid[row_i][col])
                                for row_i in cascade_rows for col in range(COLS)
                                if board.grid[row_i][col]
                            ]
                            audio.play(min(clear_count, 4))
                        else:
                            first_clear_tetris = False
                            cascade_level      = 0
                            if _spawn_next():
                                state = PLAYING
                            else:
                                _end_game()

        # ── full board cascade animation ──────────────────────────────────────
        # Blocks fall one row at a time on a timer — domino effect.
        # When nothing can fall, check for newly-formed full rows.
        elif state == CASCADING:
            cascade_anim_timer += dt
            _cascade_step = min(fall_speed(speed_tier), 300)
            if cascade_anim_timer >= _cascade_step:
                cascade_anim_timer -= _cascade_step
                if board.apply_block_gravity():
                    pass   # still falling — next frame will move the next wave
                else:
                    # Nothing moved — cascade is complete.
                    cascade_rows = board.full_rows()
                    if cascade_rows:
                        cascade_level  += 1
                        full_set        = set(cascade_rows)
                        wow_active      = all(
                            all(c == 0 for c in board.grid[r])
                            for r in range(ROWS) if r not in full_set
                        )
                        clear_rows      = full_set
                        clear_count     = len(cascade_rows)
                        clear_timer     = 0
                        clear_flash_idx = 0
                        clear_cells     = [
                            (col, row_i, board.grid[row_i][col])
                            for row_i in cascade_rows for col in range(COLS)
                            if board.grid[row_i][col]
                        ]
                        audio.play(min(clear_count, 4))
                        state = CLEARING
                    else:
                        # Cascade settled with no new rows — award cascade bonus.
                        # Base 500 pts always; grows +5000 per speed reset accumulated.
                        cascade_end_bonus = 500 + CASCADE_BONUS_PER_RESET * speed_reset_count
                        score += cascade_end_bonus
                        score_deltas.append({
                            'text':      f"+{cascade_end_bonus:,}",
                            'color':     (80, 255, 180),
                            'x':         float(BOARD_WIDTH * 0.68),
                            'y':         float(BOARD_HEIGHT * 0.45),
                            'vy':        -60.0,
                            'timer':     1600,
                            'max_timer': 1600,
                        })
                        while score >= next_speed_reset:
                            next_speed_reset  += SPEED_RESET_INTERVAL + speed_reset_count * CASCADE_INTERVAL_GROWTH
                            speed_tier         = 1
                            speed_reset_count += 1
                            reset_bonus_mult   = round(1.0 + speed_reset_count * 0.1, 1)
                            full_cascade_mode  = not full_cascade_mode
                            speed_reset_flash_timer = SPEED_RESET_FLASH_DURATION
                        best = max(best, score)
                        first_clear_tetris = False
                        cascade_level      = 0
                        if _spawn_next():
                            state = PLAYING
                        else:
                            _end_game()

        # ── game-over animation ───────────────────────────────────────────────
        if state == GAME_OVER_ANIM:
            hits = go_anim.update(dt)
            for bom_idx in hits:
                audio.play_bom(bom_idx)

        # ── popup / particle / fx timers ─────────────────────────────────────
        if popup_timer > 0:
            popup_timer = max(0, popup_timer - dt)
        particles            = update_particles(particles, dt)
        hd_flash_timer       = max(0, hd_flash_timer       - dt)
        shake_timer          = max(0, shake_timer           - dt)
        speed_reset_flash_timer = max(0, speed_reset_flash_timer - dt)
        next_flash_timer     = max(0, next_flash_timer      - dt)
        level_up_flash_timer = max(0, level_up_flash_timer  - dt)

        # Advance danger-bonus ×2 floating labels (float upward, count down).
        s = dt / 1000.0
        for db in danger_bonuses:
            db['y']     += db['vy'] * s
            db['timer'] -= dt
        danger_bonuses = [db for db in danger_bonuses if db['timer'] > 0]

        # Advance combo floating labels.
        for cl in combo_labels:
            cl['y']     += cl['vy'] * s
            cl['timer'] -= dt
        combo_labels = [cl for cl in combo_labels if cl['timer'] > 0]

        # Advance score-delta labels.
        for sd in score_deltas:
            sd['y']     += sd['vy'] * s
            sd['timer'] -= dt
        score_deltas = [sd for sd in score_deltas if sd['timer'] > 0]

        # ── draw ──────────────────────────────────────────────────────────────
        if state == MENU:
            draw_menu(screen, blink_on)

        elif state in (PLAYING, CLEARING, CASCADING, GAME_OVER, GAME_OVER_ANIM, PAUSED):
            screen.fill(BG_COLOR)

            # Palette phase: darkens tiles by 10 % per 10 levels, wraps every 6 steps.
            palette_phase = ((level - 1) // PALETTE_PHASE_INTERVAL) % 6

            # Board content draws to its own surface so shake + flash can offset it
            bsurf = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))
            bsurf.fill(_BOARD_LINE)

            fr = clear_rows if state == CLEARING else None
            fo = (clear_flash_idx % 2 == 0) if state == CLEARING else False
            fq = (clear_count == 4) if state == CLEARING else False
            fw = wow_active if state == CLEARING else False
            draw_board(bsurf, board, flash_rows=fr, flash_on=fo, flash_quad=fq,
                       wow_on=fw, palette_phase=palette_phase)

            # Danger warning line — drawn over the board but under the live piece
            # so the player can still see the boundary while actively placing blocks.
            if danger and state in (PLAYING, CLEARING, CASCADING, PAUSED):
                _draw_danger_line(bsurf)

            if state in (PLAYING, PAUSED):
                draw_ghost(bsurf, board, current, ghost_opacity_pct,
                           palette_phase=palette_phase)
                draw_piece(bsurf, current, palette_phase=palette_phase)

            draw_particles(bsurf, particles)

            # Danger-zone bonus ×2 floating labels
            for db in danger_bonuses:
                a = int(255 * db['timer'] / db['max_timer'])
                t = _font(20).render("×2", True, (255, 90, 0))
                t.set_alpha(a)
                bsurf.blit(t, (int(db['x']), int(db['y'])))

            # Combo floating labels (centred, cyan)
            for cl in combo_labels:
                a  = int(255 * cl['timer'] / cl['max_timer'])
                ct = _font(18).render(cl['text'], True, (0, 220, 240))
                ct.set_alpha(a)
                bsurf.blit(ct, (int(cl['x']), int(cl['y'])))

            # Score-delta floating labels (right-of-centre, coloured by event type)
            for sd in score_deltas:
                a   = int(255 * sd['timer'] / sd['max_timer'])
                sdt = _font(16).render(sd['text'], True, sd['color'])
                sdt.set_alpha(a)
                bsurf.blit(sdt, (int(sd['x']) - sdt.get_width() // 2, int(sd['y'])))

            # Speed-reset "SPEED RESET!" overlay (board-centred, fades out)
            if speed_reset_flash_timer > 0:
                a = 1.0 if speed_reset_flash_timer > 500 else speed_reset_flash_timer / 500
                sr_col = tuple(int(c * a) for c in (100, 255, 100))
                sr_t   = _font(22).render("SPEED  RESET!", True, sr_col)
                bsurf.blit(sr_t, (BOARD_WIDTH // 2 - sr_t.get_width() // 2, 38))

            # Hard-drop white flash
            if hd_flash_timer > 0:
                alpha = int(190 * hd_flash_timer / HD_FLASH_DURATION)
                fl = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
                fl.fill((255, 255, 255, alpha))
                bsurf.blit(fl, (0, 0))

            if state == CASCADING:
                h = (pygame.time.get_ticks() / 120) % 1.0
                rgb = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, 1.0, 1.0))
                cas_t = _font(30).render("CASCADE!", True, rgb)
                cx = BOARD_WIDTH // 2 - cas_t.get_width() // 2
                cy = BOARD_HEIGHT // 2 - cas_t.get_height() // 2
                pad = 8
                bg = pygame.Surface((cas_t.get_width() + pad * 2,
                                     cas_t.get_height() + pad * 2), pygame.SRCALPHA)
                bg.fill((0, 0, 0, 160))
                bsurf.blit(bg, (cx - pad, cy - pad))
                bsurf.blit(cas_t, (cx, cy))

            elif state == GAME_OVER:
                draw_game_over_overlay(bsurf, score,
                                       stat_pieces, stat_tetrises, stat_tspins,
                                       stat_combo, stat_time)
            elif state == GAME_OVER_ANIM:
                go_anim.draw(bsurf)

            # Screen shake (quad only) — randomise offset each frame
            ox = oy = 0
            if shake_timer > 0:
                amt = max(1, int(SHAKE_INTENSITY * shake_timer / SHAKE_DURATION))
                ox  = random.randint(-amt, amt)
                oy  = random.randint(-amt, amt)

            screen.blit(bsurf, (ox, oy))

            draw_sidebar(screen, score, lines, level, piece_queue, best,
                         hold_piece, hold_used,
                         speed_tier, next_speed_reset,
                         reset_bonus_mult, full_cascade_mode,
                         palette_phase,
                         popup_count, popup_timer,
                         next_flash_timer, hold_piece is not None,
                         combo, level_up_flash_timer)
            pygame.draw.rect(screen, BORDER_COLOR,
                             (0, 0, BOARD_WIDTH, BOARD_HEIGHT), 1)
            pygame.draw.line(screen, BORDER_COLOR,
                             (BOARD_WIDTH, 0), (BOARD_WIDTH, SCREEN_HEIGHT), 1)

            if state == PAUSED:
                draw_pause(screen, blink_on)

        elif state == ENTER_NAME:
            draw_name_entry(screen, initials, ini_cursor, blink_on,
                            score, lines, level)

        elif state == LEADERBOARD:
            draw_leaderboard(screen, lb_scores, lb_hi_name, lb_hi_score)

        elif state == SETTINGS:
            draw_settings(screen, music_vol_pct, sfx_vol_pct,
                          settings_row, music.is_muted(), current_scale,
                          ghost_opacity_pct, das_preset)

        elif state == MUSIC_TEST:
            draw_music_test(screen, music_test_tier)

        # Scale the logical surface to the actual display window
        if current_scale == 1.0:
            display.blit(screen, (0, 0))
        else:
            pygame.transform.smoothscale(screen, display.get_size(), display)
        pygame.display.flip()


if __name__ == "__main__":
    main()
