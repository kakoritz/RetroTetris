import colorsys
import random
import pygame
import sys

import audio
audio.pre_init()

import config
import highscore
import music
import music_game
from particles import spawn as spawn_particles
from particles import update as update_particles
from particles import draw as draw_particles
from constants import (
    COLS, ROWS, CELL_SIZE,
    BOARD_WIDTH, BOARD_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT,
    FPS, BG_COLOR, BORDER_COLOR, SCORE_TABLE, fall_speed,
)
import rotation
from renderer import (
    _font, _BOARD_LINE,
    draw_board, _draw_danger_line, draw_piece, draw_ghost,
    draw_sidebar, draw_game_over_overlay,
    draw_settings, draw_pause, draw_music_test,
    draw_menu, draw_name_entry, draw_leaderboard,
)
from game_constants import (
    LOCK_DELAY,
    FLASH_MS, FLASH_TOTAL,
    FLASH_MS_WOW, FLASH_TOTAL_WOW,
    WOW_BONUS, WOW_POPUP_DURATION, COLOR_CLEAR_BONUS,
    TSPIN_SCORES, TSPIN_MINI_SCORES,
    COMBO_BONUS_UNIT,
    GRAVITY_20G_LEVEL,
    SPEED_RESET_INTERVAL, CASCADE_INTERVAL_GROWTH,
    PALETTE_PHASE_INTERVAL,
    PAGE_VOL_STEP,
    SPEED_RESET_FLASH_DURATION,
    CASCADE_BONUS_PER_RESET,
    POPUP_DURATION, SHAKE_DURATION, SHAKE_INTENSITY, HD_FLASH_DURATION,
)
from game_state import GameState
from app_state import AppState
from game_logic import (
    spawn_next, do_hold, start_new_game, end_game,
    reset_lock, do_lock, debug_clear_board,
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
CASCADING      = "cascading"

_MUSIC_END      = pygame.USEREVENT + 1
_INITIALS_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ "


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
    ox, oy = 1, 6
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

    pygame.display.set_icon(_build_icon())

    current_scale = config.get_scale()
    display       = _make_display(current_scale)

    if pygame.display.get_driver() == "offscreen":
        print(
            "\nT3TR1S: display unavailable — SDL fell back to offscreen mode.\n"
            "This usually means the X server has run out of client connections\n"
            "(common when VS Code, Firefox, and Discord are all open).\n"
            "Close a few heavy apps and try again.\n"
        )
        pygame.quit()
        sys.exit(1)

    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("T3TR1S")
    clock = pygame.time.Clock()
    music.start()
    audio.prime()

    gs  = GameState()
    gs.reset()
    app = AppState(display, screen, current_scale)
    app.best = highscore.best()

    while True:
        dt = clock.tick(FPS)

        app.blink_timer += dt
        if app.blink_timer >= 500:
            app.blink_timer = 0
            app.blink_on    = not app.blink_on

        # ── events ────────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if (event.type == _MUSIC_END
                    and app.state in (PLAYING, CLEARING, CASCADING, PAUSED)):
                music_game.on_music_end()
                if app.state == PAUSED:
                    pygame.mixer.music.set_volume(app.pre_pause_vol * 0.10)

            # KEYUP: track DAS key releases regardless of state
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    app.keys_held.discard(pygame.K_LEFT)
                    if app.das_dir == -1:
                        app.das_dir = (1 if pygame.K_RIGHT in app.keys_held else 0)
                        app.das_timer = 0; app.das_charged = False
                elif event.key == pygame.K_RIGHT:
                    app.keys_held.discard(pygame.K_RIGHT)
                    if app.das_dir == 1:
                        app.das_dir = (-1 if pygame.K_LEFT in app.keys_held else 0)
                        app.das_timer = 0; app.das_charged = False

            if event.type != pygame.KEYDOWN:
                continue

            # ── global keys (any state) ───────────────────────────────────────
            if event.key == pygame.K_m:
                music.toggle_mute()
                music_game.set_muted(music.is_muted())
                continue

            if event.key == pygame.K_PAGEUP:
                app.music_vol_pct = min(100, app.music_vol_pct + PAGE_VOL_STEP)
                music.set_volume(app.music_vol_pct / 100)
                music_game.set_volume(app.music_vol_pct / 100)
                continue

            if event.key == pygame.K_PAGEDOWN:
                app.music_vol_pct = max(0, app.music_vol_pct - PAGE_VOL_STEP)
                music.set_volume(app.music_vol_pct / 100)
                music_game.set_volume(app.music_vol_pct / 100)
                continue

            # ── MENU ──────────────────────────────────────────────────────────
            if app.state == MENU:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    start_new_game(gs, app)
                    app.best = highscore.best()
                    music.fadeout(400)
                    music_game.start_sequence()
                    app.state = PLAYING
                elif event.key == pygame.K_s:
                    app.settings_row          = 0
                    app.settings_return_state = MENU
                    app.state = SETTINGS
                elif event.key == pygame.K_t:
                    app.music_test_tier = 1
                    music.fadeout(300)
                    music_game.start_level(app.music_test_tier)
                    app.state = MUSIC_TEST

            # ── PLAYING ───────────────────────────────────────────────────────
            elif app.state == PLAYING:
                # Secret 3-2-1 debug sequence: triggers a full board clear + WOW.
                _CHEAT = [pygame.K_3, pygame.K_2, pygame.K_1]
                if event.key == _CHEAT[len(app._cheat_seq)]:
                    app._cheat_seq.append(event.key)
                    if len(app._cheat_seq) == 3:
                        app._cheat_seq.clear()
                        debug_clear_board(gs, app)
                        continue
                else:
                    app._cheat_seq.clear()

                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    app.pre_pause_vol = pygame.mixer.music.get_volume()
                    pygame.mixer.music.set_volume(max(0.0, app.pre_pause_vol * 0.10))
                    app.state = PAUSED
                elif event.key == pygame.K_LEFT:
                    app.keys_held.add(pygame.K_LEFT)
                    app.das_dir = -1; app.das_timer = 0; app.das_charged = False
                    if gs.board.is_valid(gs.current, dx=-1):
                        gs.current.x -= 1
                        gs.last_action = 'move'
                        audio.play('move')
                        reset_lock(gs)
                        if gs.level >= GRAVITY_20G_LEVEL:
                            while gs.board.is_valid(gs.current, dy=1):
                                gs.current.y += 1
                elif event.key == pygame.K_RIGHT:
                    app.keys_held.add(pygame.K_RIGHT)
                    app.das_dir = 1; app.das_timer = 0; app.das_charged = False
                    if gs.board.is_valid(gs.current, dx=1):
                        gs.current.x += 1
                        gs.last_action = 'move'
                        audio.play('move')
                        reset_lock(gs)
                        if gs.level >= GRAVITY_20G_LEVEL:
                            while gs.board.is_valid(gs.current, dy=1):
                                gs.current.y += 1
                elif event.key == pygame.K_DOWN:
                    if gs.board.is_valid(gs.current, dy=1):
                        gs.current.y += 1
                        gs.score      += 1
                        gs.last_action = 'soft_drop'
                        gs.lock_timer  = 0
                elif event.key == pygame.K_UP:
                    if event.mod & pygame.KMOD_CTRL:
                        if rotation.try_rotate(gs.board, gs.current, *gs.current.rotated_ccw()):
                            gs.last_action = 'rotate'
                            reset_lock(gs)
                    else:
                        if rotation.try_rotate(gs.board, gs.current, *gs.current.rotated_cw()):
                            gs.last_action = 'rotate'
                            reset_lock(gs)
                elif event.key == pygame.K_z:
                    if rotation.try_rotate(gs.board, gs.current, *gs.current.rotated_ccw()):
                        gs.last_action = 'rotate'
                        reset_lock(gs)
                elif event.key == pygame.K_c:
                    do_hold(gs, app)
                elif event.key == pygame.K_SPACE:
                    gs.hd_flash_timer = HD_FLASH_DURATION
                    _hd_start_y = gs.current.y
                    while gs.board.is_valid(gs.current, dy=1):
                        gs.current.y += 1
                    gs.score      += (gs.current.y - _hd_start_y) * 2
                    gs.last_action = 'hard_drop'
                    audio.play('hard_drop')
                    gs.fall_timer  = 0
                    do_lock(gs, app)

            # ── GAME OVER ANIM (press any key to continue) ────────────────────
            elif app.state == GAME_OVER_ANIM:
                if app.go_anim.all_landed:
                    app.state = app.post_anim_state

            # ── PAUSED ────────────────────────────────────────────────────────
            elif app.state == PAUSED:
                if event.key == pygame.K_q:
                    music_game.stop()
                    music.start_menu()
                    app.state = MENU
                elif event.key == pygame.K_SPACE:
                    pygame.mixer.music.set_volume(app.pre_pause_vol)
                    app.state = PLAYING
                elif event.key == pygame.K_s:
                    pygame.mixer.music.set_volume(app.pre_pause_vol)
                    app.settings_row          = 0
                    app.settings_return_state = PAUSED
                    app.state = SETTINGS

            # ── GAME OVER ─────────────────────────────────────────────────────
            elif app.state == GAME_OVER:
                if event.key == pygame.K_r:
                    start_new_game(gs, app)
                    music_game.stop()
                    music_game.start_sequence()
                    app.state = PLAYING
                elif event.key in (pygame.K_SPACE, pygame.K_ESCAPE):
                    music_game.stop()
                    music.start_menu()
                    app.state = MENU
                elif event.key == pygame.K_l:
                    app.lb_scores   = highscore.load()
                    app.lb_hi_name  = app.lb_hi_score = None
                    app.state       = LEADERBOARD

            # ── ENTER NAME ────────────────────────────────────────────────────
            elif app.state == ENTER_NAME:
                idx = _INITIALS_CHARS
                if event.key == pygame.K_UP:
                    pos = (idx.index(app.initials[app.ini_cursor]) - 1) % len(idx)
                    app.initials[app.ini_cursor] = idx[pos]
                elif event.key == pygame.K_DOWN:
                    pos = (idx.index(app.initials[app.ini_cursor]) + 1) % len(idx)
                    app.initials[app.ini_cursor] = idx[pos]
                elif event.key == pygame.K_LEFT and app.ini_cursor > 0:
                    app.ini_cursor -= 1
                elif event.key in (pygame.K_RIGHT, pygame.K_RETURN, pygame.K_KP_ENTER):
                    if app.ini_cursor < 2:
                        app.ini_cursor += 1
                    else:
                        name            = ''.join(app.initials).strip() or "???"
                        app.lb_scores   = highscore.insert(name, gs.score, gs.lines, gs.level)
                        app.lb_hi_name  = name
                        app.lb_hi_score = gs.score
                        app.best        = highscore.best()
                        app.state       = LEADERBOARD
                elif pygame.K_a <= event.key <= pygame.K_z:
                    app.initials[app.ini_cursor] = chr(event.key).upper()
                    if app.ini_cursor < 2:
                        app.ini_cursor += 1

            # ── LEADERBOARD ───────────────────────────────────────────────────
            elif app.state == LEADERBOARD:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                    music_game.stop()
                    music.start_menu()
                    app.state = MENU
                elif event.key == pygame.K_r:
                    start_new_game(gs, app)
                    music_game.stop()
                    music_game.start_sequence()
                    app.state = PLAYING

            # ── MUSIC PREVIEW ─────────────────────────────────────────────────
            elif app.state == MUSIC_TEST:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN,
                                 pygame.K_KP_ENTER):
                    music_game.stop()
                    music.start_menu()
                    app.state = MENU
                elif event.key == pygame.K_UP:
                    app.music_test_tier = max(1, app.music_test_tier - 1)
                    music_game.start_level(app.music_test_tier)
                elif event.key == pygame.K_DOWN:
                    app.music_test_tier = min(10, app.music_test_tier + 1)
                    music_game.start_level(app.music_test_tier)

            # ── SETTINGS ──────────────────────────────────────────────────────
            elif app.state == SETTINGS:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                    if app.settings_return_state == PAUSED:
                        app.pre_pause_vol = app.music_vol_pct / 100
                        pygame.mixer.music.set_volume(max(0.0, app.pre_pause_vol * 0.10))
                        app.state = PAUSED
                    else:
                        app.state = MENU
                elif event.key == pygame.K_UP:
                    app.settings_row = (app.settings_row - 1) % 5
                elif event.key == pygame.K_DOWN:
                    app.settings_row = (app.settings_row + 1) % 5
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    delta = -5 if event.key == pygame.K_LEFT else 5
                    if app.settings_row == 0:
                        app.music_vol_pct = max(0, min(100, app.music_vol_pct + delta))
                        music.set_volume(app.music_vol_pct / 100)
                        music_game.set_volume(app.music_vol_pct / 100)
                    elif app.settings_row == 1:
                        app.sfx_vol_pct = max(0, min(100, app.sfx_vol_pct + delta))
                        audio.set_sfx_volume(app.sfx_vol_pct / 100)
                        audio.play('rotate')
                    elif app.settings_row == 2:
                        scales = config.VALID_SCALES
                        idx = scales.index(app.current_scale) if app.current_scale in scales else 0
                        idx = max(0, min(len(scales) - 1,
                                        idx + (1 if event.key == pygame.K_RIGHT else -1)))
                        new_scale = scales[idx]
                        if new_scale != app.current_scale:
                            app.current_scale = new_scale
                            config.set_scale(app.current_scale)
                            app.display = _make_display(app.current_scale)
                    elif app.settings_row == 3:
                        app.ghost_opacity_pct = max(0, min(100, app.ghost_opacity_pct + delta))
                        config.set_ghost_opacity(app.ghost_opacity_pct)
                    else:
                        presets = config.VALID_DAS_PRESETS
                        idx = presets.index(app.das_preset) if app.das_preset in presets else 1
                        idx = max(0, min(len(presets) - 1,
                                        idx + (1 if event.key == pygame.K_RIGHT else -1)))
                        app.das_preset               = presets[idx]
                        app.das_delay, app.das_repeat = config.DAS_SETTINGS[app.das_preset]
                        config.set_das_preset(app.das_preset)

        # ── DAS auto-repeat ───────────────────────────────────────────────────
        if app.state == PLAYING and app.das_dir != 0:
            app.das_timer += dt
            if not app.das_charged:
                if app.das_timer >= app.das_delay:
                    app.das_charged = True
                    app.das_timer   = 0
            else:
                if app.das_repeat == 0:
                    if gs.board.is_valid(gs.current, dx=app.das_dir):
                        gs.current.x += app.das_dir
                        gs.last_action = 'move'
                        audio.play('move')
                        reset_lock(gs)
                        if gs.level >= GRAVITY_20G_LEVEL:
                            while gs.board.is_valid(gs.current, dy=1):
                                gs.current.y += 1
                else:
                    while app.das_timer >= app.das_repeat:
                        app.das_timer -= app.das_repeat
                        if gs.board.is_valid(gs.current, dx=app.das_dir):
                            gs.current.x += app.das_dir
                            gs.last_action = 'move'
                            audio.play('move')
                            reset_lock(gs)
                            if gs.level >= GRAVITY_20G_LEVEL:
                                while gs.board.is_valid(gs.current, dy=1):
                                    gs.current.y += 1

        # ── danger detection → tier-1 tension music + warning line ──────────
        if app.state in (PLAYING, CLEARING, CASCADING):
            gs.danger = any(any(row) for row in gs.board.grid[:10])
            music_game.set_danger(gs.danger)

        # ── gravity + lock delay ─────────────────────────────────────────────
        if app.state == PLAYING:
            grounded = not gs.board.is_valid(gs.current, dy=1)

            gs.fall_timer += dt
            if gs.fall_timer >= fall_speed(gs.speed_tier):
                gs.fall_timer = 0
                if not grounded:
                    if gs.level >= GRAVITY_20G_LEVEL:
                        while gs.board.is_valid(gs.current, dy=1):
                            gs.current.y += 1
                    else:
                        gs.current.y  += 1
                        gs.lock_timer  = 0
                    gs.last_action = 'gravity'

            grounded = not gs.board.is_valid(gs.current, dy=1)
            if grounded:
                gs.lock_timer += dt
                if gs.lock_timer >= LOCK_DELAY:
                    do_lock(gs, app)

        # ── line-clear animation ──────────────────────────────────────────────
        elif app.state == CLEARING:
            gs.clear_timer += dt
            fms    = FLASH_MS_WOW    if gs.wow_active else FLASH_MS.get(gs.clear_count, 80)
            ftotal = FLASH_TOTAL_WOW if gs.wow_active else FLASH_TOTAL.get(gs.clear_count, 2)
            if gs.clear_timer >= fms:
                gs.clear_timer -= fms
                gs.clear_flash_idx += 1
                if gs.clear_flash_idx >= ftotal:
                    # ── scoring ───────────────────────────────────────────────
                    gs.lines += gs.clear_count

                    danger_rows  = [r for r in gs.clear_rows if r < 10]
                    danger_mult  = 2 if danger_rows else 1
                    cascade_mult = min(gs.cascade_level + 1, 4)

                    is_tspin     = gs.tspin_type is not None and not gs.wow_active
                    is_difficult = (gs.clear_count == 4 or is_tspin) and not gs.wow_active
                    if is_tspin:
                        tbl        = TSPIN_MINI_SCORES if gs.tspin_type == 'mini' else TSPIN_SCORES
                        base_score = tbl.get(gs.clear_count, 0) * (gs.level + 1)
                    else:
                        base_score = SCORE_TABLE.get(gs.clear_count, 0) * (gs.level + 1)

                    tetris_x_tetris = (gs.cascade_level == 1
                                       and gs.clear_count == 4
                                       and gs.first_clear_tetris)
                    if tetris_x_tetris:
                        cascade_mult = 4

                    btb_bonus = is_difficult and gs.btb_active
                    if btb_bonus:
                        base_score = int(base_score * 1.5)

                    clear_delta = int(base_score * cascade_mult * danger_mult * gs.reset_bonus_mult)
                    gs.score   += clear_delta

                    if clear_delta > 0:
                        if is_tspin and btb_bonus:
                            _dcol = (220, 130, 255)
                        elif is_tspin:
                            _dcol = (200, 100, 255)
                        elif btb_bonus:
                            _dcol = (255, 215, 0)
                        elif gs.cascade_level > 0:
                            _dcol = (80, 255, 180)
                        elif danger_mult == 2:
                            _dcol = (255, 140, 0)
                        else:
                            _dcol = (220, 220, 255)
                        gs.score_deltas.append({
                            'text':      f"+{clear_delta:,}",
                            'color':     _dcol,
                            'x':         float(BOARD_WIDTH * 0.68),
                            'y':         float(BOARD_HEIGHT * 0.52),
                            'vy':        -70.0,
                            'timer':     1600,
                            'max_timer': 1600,
                        })

                    combo_bonus = COMBO_BONUS_UNIT * gs.combo * (gs.level + 1)
                    gs.score   += combo_bonus
                    if gs.combo >= 1:
                        gs.combo_labels.append({
                            'text':      f"COMBO ×{gs.combo + 1}",
                            'x':         float(BOARD_WIDTH // 2 - 32),
                            'y':         float(BOARD_HEIGHT // 2),
                            'vy':        -90.0,
                            'timer':     1400,
                            'max_timer': 1400,
                        })
                    gs.combo     += 1
                    gs.stat_combo = max(gs.stat_combo, gs.combo)

                    if gs.clear_count == 4:
                        gs.stat_tetrises += 1
                    if is_tspin:
                        gs.stat_tspins += 1

                    if gs.wow_active:
                        gs.score += WOW_BONUS * (gs.level + 1)

                    if is_difficult:
                        gs.btb_active = True
                    elif not gs.wow_active and gs.clear_count > 0:
                        gs.btb_active = False

                    for r in danger_rows:
                        gs.danger_bonuses.append({
                            'x':         float(random.randint(10, BOARD_WIDTH - 50)),
                            'y':         float(r * CELL_SIZE),
                            'vy':        -115.0,
                            'timer':     1300,
                            'max_timer': 1300,
                        })

                    old_level = gs.level
                    gs.level  = gs.lines // 10 + 1
                    if gs.level > old_level:
                        gs.speed_tier = min(gs.speed_tier + (gs.level - old_level), 20)
                        gs.level_up_flash_timer = 700
                        if old_level < GRAVITY_20G_LEVEL <= gs.level:
                            gs.popup_count = 14
                            gs.popup_timer = int(POPUP_DURATION * 1.5)

                    speed_reset_triggered = False
                    while gs.score >= gs.next_speed_reset:
                        gs.next_speed_reset  += SPEED_RESET_INTERVAL + gs.speed_reset_count * CASCADE_INTERVAL_GROWTH
                        gs.speed_tier         = 1
                        gs.speed_reset_count += 1
                        gs.reset_bonus_mult   = round(1.0 + gs.speed_reset_count * 0.1, 1)
                        gs.full_cascade_mode  = not gs.full_cascade_mode
                        speed_reset_triggered = True
                    if speed_reset_triggered:
                        gs.speed_reset_flash_timer = SPEED_RESET_FLASH_DURATION

                    app.best = max(app.best, gs.score)

                    if gs.cascade_level == 0:
                        gs.first_clear_tetris = (gs.clear_count == 4)

                    # ── clear lines ───────────────────────────────────────────
                    gs.board.clear_lines()

                    # ── color clear: blast every remaining cell of that color ──
                    _had_color_clear = False
                    if gs.color_clear_id is not None:
                        cc_removed = gs.board.remove_color(gs.color_clear_id)
                        gs.color_clear_id = None
                        if cc_removed:
                            gs.particles     += spawn_particles(cc_removed, 4)
                            gs.score         += COLOR_CLEAR_BONUS
                            app.best          = max(app.best, gs.score)
                            _had_color_clear  = True

                    # ── visual feedback for THIS clear pass ───────────────────
                    big_clear = (gs.wow_active or gs.clear_count == 4
                                 or (is_tspin and gs.clear_count == 3)
                                 or tetris_x_tetris)
                    gs.particles += spawn_particles(gs.clear_cells, gs.clear_count)
                    if big_clear:
                        gs.shake_timer = SHAKE_DURATION

                    # ── popup selection ───────────────────────────────────────
                    if gs.wow_active:
                        gs.popup_count = 0
                        gs.popup_timer = WOW_POPUP_DURATION
                        gs.wow_active  = False
                    elif _had_color_clear:
                        gs.popup_count = 15
                        gs.popup_timer = WOW_POPUP_DURATION
                    elif tetris_x_tetris:
                        gs.popup_count = 13
                        gs.popup_timer = WOW_POPUP_DURATION
                    elif is_tspin and btb_bonus:
                        gs.popup_count = 8
                        gs.popup_timer = POPUP_DURATION
                    elif is_tspin and gs.tspin_type == 'full':
                        gs.popup_count = 5
                        gs.popup_timer = POPUP_DURATION
                    elif is_tspin:
                        gs.popup_count = 6
                        gs.popup_timer = POPUP_DURATION
                    elif btb_bonus and gs.clear_count == 4:
                        gs.popup_count = 7
                        gs.popup_timer = POPUP_DURATION
                    elif gs.cascade_level >= 4:
                        gs.popup_count = 12
                        gs.popup_timer = POPUP_DURATION
                    elif gs.cascade_level == 3:
                        gs.popup_count = 11
                        gs.popup_timer = POPUP_DURATION
                    elif gs.cascade_level == 2:
                        gs.popup_count = 10
                        gs.popup_timer = POPUP_DURATION
                    elif gs.cascade_level == 1:
                        gs.popup_count = 9
                        gs.popup_timer = POPUP_DURATION
                    else:
                        gs.popup_count = gs.clear_count
                        gs.popup_timer = POPUP_DURATION

                    gs.tspin_type = None

                    # ── cascade check ─────────────────────────────────────────
                    if gs.full_cascade_mode:
                        app.cascade_anim_timer = 0
                        app.state = CASCADING
                    else:
                        gs.board.settle_blocks()
                        cascade_rows = gs.board.full_rows()
                        if cascade_rows:
                            gs.cascade_level += 1
                            full_set          = set(cascade_rows)
                            gs.wow_active     = all(
                                all(c == 0 for c in gs.board.grid[r])
                                for r in range(ROWS) if r not in full_set
                            )
                            gs.clear_rows      = full_set
                            gs.clear_count     = len(cascade_rows)
                            gs.clear_timer     = 0
                            gs.clear_flash_idx = 0
                            gs.clear_cells     = [
                                (col, row_i, gs.board.grid[row_i][col])
                                for row_i in cascade_rows for col in range(COLS)
                                if gs.board.grid[row_i][col]
                            ]
                            audio.play(min(gs.clear_count, 4))
                        else:
                            gs.first_clear_tetris = False
                            gs.cascade_level      = 0
                            if spawn_next(gs, app):
                                app.state = PLAYING
                            else:
                                end_game(gs, app)

        # ── full board cascade animation ──────────────────────────────────────
        elif app.state == CASCADING:
            app.cascade_anim_timer += dt
            _cascade_step = min(fall_speed(gs.speed_tier), 300)
            if app.cascade_anim_timer >= _cascade_step:
                app.cascade_anim_timer -= _cascade_step
                if gs.board.apply_block_gravity():
                    pass
                else:
                    cascade_rows = gs.board.full_rows()
                    if cascade_rows:
                        gs.cascade_level += 1
                        full_set          = set(cascade_rows)
                        gs.wow_active     = all(
                            all(c == 0 for c in gs.board.grid[r])
                            for r in range(ROWS) if r not in full_set
                        )
                        gs.clear_rows      = full_set
                        gs.clear_count     = len(cascade_rows)
                        gs.clear_timer     = 0
                        gs.clear_flash_idx = 0
                        gs.clear_cells     = [
                            (col, row_i, gs.board.grid[row_i][col])
                            for row_i in cascade_rows for col in range(COLS)
                            if gs.board.grid[row_i][col]
                        ]
                        audio.play(min(gs.clear_count, 4))
                        app.state = CLEARING
                    else:
                        cascade_end_bonus = 500 + CASCADE_BONUS_PER_RESET * gs.speed_reset_count
                        gs.score += cascade_end_bonus
                        gs.score_deltas.append({
                            'text':      f"+{cascade_end_bonus:,}",
                            'color':     (80, 255, 180),
                            'x':         float(BOARD_WIDTH * 0.68),
                            'y':         float(BOARD_HEIGHT * 0.45),
                            'vy':        -60.0,
                            'timer':     1600,
                            'max_timer': 1600,
                        })
                        while gs.score >= gs.next_speed_reset:
                            gs.next_speed_reset  += SPEED_RESET_INTERVAL + gs.speed_reset_count * CASCADE_INTERVAL_GROWTH
                            gs.speed_tier         = 1
                            gs.speed_reset_count += 1
                            gs.reset_bonus_mult   = round(1.0 + gs.speed_reset_count * 0.1, 1)
                            gs.full_cascade_mode  = not gs.full_cascade_mode
                            gs.speed_reset_flash_timer = SPEED_RESET_FLASH_DURATION
                        app.best               = max(app.best, gs.score)
                        gs.first_clear_tetris  = False
                        gs.cascade_level       = 0
                        if spawn_next(gs, app):
                            app.state = PLAYING
                        else:
                            end_game(gs, app)

        # ── game-over animation ───────────────────────────────────────────────
        if app.state == GAME_OVER_ANIM:
            hits = app.go_anim.update(dt)
            for bom_idx in hits:
                audio.play_bom(bom_idx)

        # ── popup / particle / fx timers ─────────────────────────────────────
        if gs.popup_timer > 0:
            gs.popup_timer = max(0, gs.popup_timer - dt)
        gs.particles             = update_particles(gs.particles, dt)
        gs.hd_flash_timer        = max(0, gs.hd_flash_timer        - dt)
        gs.shake_timer           = max(0, gs.shake_timer            - dt)
        gs.speed_reset_flash_timer = max(0, gs.speed_reset_flash_timer - dt)
        gs.next_flash_timer      = max(0, gs.next_flash_timer       - dt)
        gs.level_up_flash_timer  = max(0, gs.level_up_flash_timer   - dt)

        s = dt / 1000.0
        for db in gs.danger_bonuses:
            db['y']     += db['vy'] * s
            db['timer'] -= dt
        gs.danger_bonuses = [db for db in gs.danger_bonuses if db['timer'] > 0]

        for cl in gs.combo_labels:
            cl['y']     += cl['vy'] * s
            cl['timer'] -= dt
        gs.combo_labels = [cl for cl in gs.combo_labels if cl['timer'] > 0]

        for sd in gs.score_deltas:
            sd['y']     += sd['vy'] * s
            sd['timer'] -= dt
        gs.score_deltas = [sd for sd in gs.score_deltas if sd['timer'] > 0]

        # ── draw ──────────────────────────────────────────────────────────────
        if app.state == MENU:
            draw_menu(app.screen, app.blink_on)

        elif app.state in (PLAYING, CLEARING, CASCADING, GAME_OVER, GAME_OVER_ANIM, PAUSED):
            app.screen.fill(BG_COLOR)

            palette_phase = ((gs.level - 1) // PALETTE_PHASE_INTERVAL) % 6

            bsurf = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))
            bsurf.fill(_BOARD_LINE)

            fr = gs.clear_rows if app.state == CLEARING else None
            fo = (gs.clear_flash_idx % 2 == 0) if app.state == CLEARING else False
            fq = (gs.clear_count == 4) if app.state == CLEARING else False
            fw = gs.wow_active if app.state == CLEARING else False
            draw_board(bsurf, gs.board, flash_rows=fr, flash_on=fo, flash_quad=fq,
                       wow_on=fw, palette_phase=palette_phase)

            if gs.danger and app.state in (PLAYING, CLEARING, CASCADING, PAUSED):
                _draw_danger_line(bsurf)

            if app.state in (PLAYING, PAUSED):
                draw_ghost(bsurf, gs.board, gs.current, app.ghost_opacity_pct,
                           palette_phase=palette_phase)
                draw_piece(bsurf, gs.current, palette_phase=palette_phase)

            draw_particles(bsurf, gs.particles)

            for db in gs.danger_bonuses:
                a = int(255 * db['timer'] / db['max_timer'])
                t = _font(20).render("×2", True, (255, 90, 0))
                t.set_alpha(a)
                bsurf.blit(t, (int(db['x']), int(db['y'])))

            for cl in gs.combo_labels:
                a  = int(255 * cl['timer'] / cl['max_timer'])
                ct = _font(18).render(cl['text'], True, (0, 220, 240))
                ct.set_alpha(a)
                bsurf.blit(ct, (int(cl['x']), int(cl['y'])))

            for sd in gs.score_deltas:
                a   = int(255 * sd['timer'] / sd['max_timer'])
                sdt = _font(16).render(sd['text'], True, sd['color'])
                sdt.set_alpha(a)
                bsurf.blit(sdt, (int(sd['x']) - sdt.get_width() // 2, int(sd['y'])))

            if gs.speed_reset_flash_timer > 0:
                a      = 1.0 if gs.speed_reset_flash_timer > 500 else gs.speed_reset_flash_timer / 500
                sr_col = tuple(int(c * a) for c in (100, 255, 100))
                sr_t   = _font(22).render("SPEED  RESET!", True, sr_col)
                bsurf.blit(sr_t, (BOARD_WIDTH // 2 - sr_t.get_width() // 2, 38))

            if gs.hd_flash_timer > 0:
                alpha = int(190 * gs.hd_flash_timer / HD_FLASH_DURATION)
                fl    = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
                fl.fill((255, 255, 255, alpha))
                bsurf.blit(fl, (0, 0))

            if app.state == CASCADING:
                h   = (pygame.time.get_ticks() / 120) % 1.0
                rgb = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, 1.0, 1.0))
                cas_t = _font(30).render("CASCADE!", True, rgb)
                cx    = BOARD_WIDTH  // 2 - cas_t.get_width()  // 2
                cy    = BOARD_HEIGHT // 2 - cas_t.get_height() // 2
                pad   = 8
                bg    = pygame.Surface((cas_t.get_width() + pad * 2,
                                        cas_t.get_height() + pad * 2), pygame.SRCALPHA)
                bg.fill((0, 0, 0, 160))
                bsurf.blit(bg, (cx - pad, cy - pad))
                bsurf.blit(cas_t, (cx, cy))

            elif app.state == GAME_OVER:
                draw_game_over_overlay(bsurf, gs.score,
                                       gs.stat_pieces, gs.stat_tetrises, gs.stat_tspins,
                                       gs.stat_combo, gs.stat_time)
            elif app.state == GAME_OVER_ANIM:
                app.go_anim.draw(bsurf)

            ox = oy = 0
            if gs.shake_timer > 0:
                amt = max(1, int(SHAKE_INTENSITY * gs.shake_timer / SHAKE_DURATION))
                ox  = random.randint(-amt, amt)
                oy  = random.randint(-amt, amt)

            app.screen.blit(bsurf, (ox, oy))

            draw_sidebar(app.screen, gs.score, gs.lines, gs.level, gs.piece_queue,
                         app.best, gs.hold_piece, gs.hold_used,
                         gs.speed_tier, gs.next_speed_reset,
                         gs.reset_bonus_mult, gs.full_cascade_mode,
                         palette_phase,
                         gs.popup_count, gs.popup_timer,
                         gs.next_flash_timer, gs.hold_piece is not None,
                         gs.combo, gs.level_up_flash_timer)
            pygame.draw.rect(app.screen, BORDER_COLOR,
                             (0, 0, BOARD_WIDTH, BOARD_HEIGHT), 1)
            pygame.draw.line(app.screen, BORDER_COLOR,
                             (BOARD_WIDTH, 0), (BOARD_WIDTH, SCREEN_HEIGHT), 1)

            if app.state == PAUSED:
                draw_pause(app.screen, app.blink_on)

        elif app.state == ENTER_NAME:
            draw_name_entry(app.screen, app.initials, app.ini_cursor, app.blink_on,
                            gs.score, gs.lines, gs.level)

        elif app.state == LEADERBOARD:
            draw_leaderboard(app.screen, app.lb_scores, app.lb_hi_name, app.lb_hi_score)

        elif app.state == SETTINGS:
            draw_settings(app.screen, app.music_vol_pct, app.sfx_vol_pct,
                          app.settings_row, music.is_muted(), app.current_scale,
                          app.ghost_opacity_pct, app.das_preset)

        elif app.state == MUSIC_TEST:
            draw_music_test(app.screen, app.music_test_tier)

        if app.current_scale == 1.0:
            app.display.blit(app.screen, (0, 0))
        else:
            pygame.transform.smoothscale(app.screen, app.display.get_size(), app.display)
        pygame.display.flip()


if __name__ == "__main__":
    main()
