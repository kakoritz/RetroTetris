# renderer.py — all draw_* functions, extracted from main.py
import colorsys
import math
import random
import pygame

import config
from constants import (
    COLS, ROWS, CELL_SIZE,
    BOARD_WIDTH, BOARD_HEIGHT, SIDEBAR_WIDTH, SCREEN_WIDTH, SCREEN_HEIGHT,
    BG_COLOR, BORDER_COLOR, WHITE, YELLOW, COLORS, SHAPES,
)
from board import Board
from piece import Piece
from sprites import get_block, get_ghost
from game_constants import (
    FLASH_COLOR_NORM, FLASH_COLOR_QUAD,
    WOW_POPUP_DURATION, POPUP_DURATION,
    SPEED_RESET_INTERVAL,
    POPUP_STYLES,
)

# ── rendering-only constants ──────────────────────────────────────────────────

# Board background colors (Tron dark grid)
_BOARD_LINE = (0, 38, 65)    # dark-cyan shown in the 1 px gaps between cells
_BOARD_CELL = (5, 5, 18)     # near-black cell fill

# Pixel-font glyphs for the PAUSE overlay (5×5 grids)
_PAUSE_GLYPHS = {
    'P': [[1,1,1,1,0],
          [1,0,0,0,1],
          [1,1,1,1,0],
          [1,0,0,0,0],
          [1,0,0,0,0]],
    'A': [[0,1,1,0,0],
          [1,0,0,1,0],
          [1,1,1,1,0],
          [1,0,0,1,0],
          [1,0,0,1,0]],
    'U': [[1,0,0,0,1],
          [1,0,0,0,1],
          [1,0,0,0,1],
          [1,0,0,0,1],
          [0,1,1,1,0]],
    'S': [[0,1,1,1,0],
          [1,0,0,0,0],
          [0,1,1,0,0],
          [0,0,0,1,0],
          [1,1,1,0,0]],
    'E': [[1,1,1,1,0],
          [1,0,0,0,0],
          [1,1,1,0,0],
          [1,0,0,0,0],
          [1,1,1,1,0]],
}
_PAUSE_COLORS = [
    (0, 240, 240),
    (240, 240, 0),
    (160, 0, 240),
    (0, 240, 0),
    (240, 0, 0),
]
_PAUSE_BLOCK = 12   # px block size for PAUSE text
_PAUSE_CELL  = 14   # block + 2 px gap

_TIER_DESC = {
    1:  "whole-note bass pulse",
    2:  "quarter-note walking bass",
    3:  "8th-note Am groove",
    4:  "chord movement bass  (Am / F / G)",
    5:  "bass + Am arpeggio",
    6:  "bass + full chord arpeggio",
    7:  "bass + arp + melody layer 1",
    8:  "bass + arp + melody layers 1 & 2",
    9:  "syncopated bass + full arrangement",
    10: "full arrangement + sparkle highs",
}

_TITLE_COLORS = [
    (160,   0, 240),
    (  0, 240, 240),
    (240, 240,   0),
    (  0, 240,   0),
    (  0,  60, 240),
    (240,   0,   0),
]

# ── font cache ────────────────────────────────────────────────────────────────

_font_cache: dict = {}

def _font(size: int, bold: bool = True) -> pygame.font.Font:
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont("monospace", size, bold=bold)
    return _font_cache[key]


# ── board / piece drawing ─────────────────────────────────────────────────────

def draw_board(surf: pygame.Surface, board: Board,
               flash_rows: set | None = None,
               flash_on: bool = False,
               flash_quad: bool = False,
               wow_on: bool = False,
               palette_phase: int = 0) -> None:
    if wow_on and flash_on:
        h = (pygame.time.get_ticks() / 90) % 1.0   # ~11 Hz hue cycle
        r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
        fc = (int(r * 255), int(g * 255), int(b * 255))
    elif flash_quad:
        fc = FLASH_COLOR_QUAD
    else:
        fc = FLASH_COLOR_NORM

    for gy, row in enumerate(board.grid):
        for gx, val in enumerate(row):
            px, py = gx * CELL_SIZE, gy * CELL_SIZE
            if wow_on and flash_on:
                pygame.draw.rect(surf, fc, (px, py, CELL_SIZE - 1, CELL_SIZE - 1))
            elif flash_rows and gy in flash_rows and flash_on:
                pygame.draw.rect(surf, fc, (px, py, CELL_SIZE - 1, CELL_SIZE - 1))
            elif val:
                surf.blit(get_block(val, palette_phase=palette_phase), (px, py))
            else:
                pygame.draw.rect(surf, _BOARD_CELL,
                                 (px, py, CELL_SIZE - 1, CELL_SIZE - 1))


def _draw_danger_line(surf: pygame.Surface) -> None:
    y = 10 * CELL_SIZE
    t = pygame.time.get_ticks()
    pulse = 0.5 + 0.5 * math.sin(t * 0.016)
    r     = 255
    gb    = int(20 + 30 * pulse)
    col   = (r, gb, gb)
    pygame.draw.line(surf, col, (0, y),     (BOARD_WIDTH - 1, y),     2)
    glow = (int(r * 0.28), int(gb * 0.28), int(gb * 0.28))
    pygame.draw.line(surf, glow, (0, y - 1), (BOARD_WIDTH - 1, y - 1), 1)
    pygame.draw.line(surf, glow, (0, y + 2), (BOARD_WIDTH - 1, y + 2), 1)


def draw_piece(surf: pygame.Surface, piece: Piece,
               palette_phase: int = 0) -> None:
    for row_i, row in enumerate(piece.shape):
        for col_i, val in enumerate(row):
            if val:
                surf.blit(get_block(val, palette_phase=palette_phase),
                          ((piece.x + col_i) * CELL_SIZE,
                           (piece.y + row_i) * CELL_SIZE))


def draw_ghost(surf: pygame.Surface, board: Board, piece: Piece,
               opacity_pct: int = 25, palette_phase: int = 0) -> None:
    if opacity_pct == 0:
        return
    gy = board.ghost_y(piece)
    if gy == piece.y:
        return
    for row_i, row in enumerate(piece.shape):
        for col_i, val in enumerate(row):
            if val:
                surf.blit(get_ghost(val, opacity_pct=opacity_pct,
                                    palette_phase=palette_phase),
                          ((piece.x + col_i) * CELL_SIZE,
                           (gy + row_i) * CELL_SIZE))


# ── popup ─────────────────────────────────────────────────────────────────────

def draw_popup(surf: pygame.Surface, count: int, timer: int) -> None:
    if timer <= 0 or count not in POPUP_STYLES:
        return
    text_str, base_color, base_size = POPUP_STYLES[count]

    is_wow   = (count in (0, 13, 15))
    duration = WOW_POPUP_DURATION if is_wow else POPUP_DURATION
    elapsed  = duration - timer

    if is_wow:
        y = BOARD_HEIGHT // 2 - 18 - int((elapsed / duration) * 40)
    else:
        start_y = int(BOARD_HEIGHT * 0.62)
        y = start_y - int((elapsed / POPUP_DURATION) * 60)

    alpha = 1.0 if timer > 600 else timer / 600
    size  = base_size + (5 if elapsed < 200 else 0)

    if base_color is None:
        speed = 200 if is_wow else 450
        h = (pygame.time.get_ticks() / speed) % 1.0
        r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
        vivid = (int(r * 255), int(g * 255), int(b * 255))
    else:
        vivid = base_color

    color = tuple(int(c * alpha) for c in vivid)
    f     = _font(size)
    tw, th = f.size(text_str)

    pad_x = 14 if is_wow else 10
    pad_y = 7  if is_wow else 4
    bw, bh = tw + pad_x * 2, th + pad_y * 2
    bx = BOARD_WIDTH // 2 - bw // 2
    bg_alpha = 0.30 if is_wow else 0.22
    bg = tuple(int(c * bg_alpha * alpha) for c in vivid)
    pygame.draw.rect(surf, bg, (bx, y - pad_y, bw, bh), border_radius=6)
    shadow = tuple(int(c * 0.25 * alpha) for c in vivid)
    t = f.render(text_str, True, shadow)
    surf.blit(t, (BOARD_WIDTH // 2 - tw // 2 + 2, y + 2))
    t = f.render(text_str, True, color)
    surf.blit(t, (BOARD_WIDTH // 2 - tw // 2, y))


# ── sidebar ───────────────────────────────────────────────────────────────────

def draw_sidebar(surf: pygame.Surface, score: int, lines: int,
                 level: int, piece_queue: list, best: int,
                 hold_piece=None, hold_used: bool = False,
                 speed_tier: int = 1, next_speed_reset: int = SPEED_RESET_INTERVAL,
                 reset_bonus_mult: float = 1.0, full_cascade_mode: bool = False,
                 palette_phase: int = 0,
                 popup_count: int = 0, popup_timer: int = 0,
                 next_flash_timer: int = 0, hold_has_piece: bool = False,
                 combo: int = 0, level_up_flash_timer: int = 0) -> None:
    sx = BOARD_WIDTH + 12

    def lbl(text, y): surf.blit(_font(13).render(text, True, BORDER_COLOR), (sx, y))
    def val(text, y): surf.blit(_font(19).render(text, True, YELLOW),       (sx, y))

    lbl("SCORE", 14); val(str(score).zfill(7), 30)
    lbl("BEST",  60); val(str(best).zfill(7),  76)

    surf.blit(_font(12).render("LVL",   True, BORDER_COLOR), (sx,      108))
    surf.blit(_font(12).render("LINES", True, BORDER_COLOR), (sx + 65, 108))
    level_col = WHITE if level_up_flash_timer > 0 else YELLOW
    surf.blit(_font(17).render(str(level), True, level_col), (sx,      122))
    surf.blit(_font(17).render(str(lines), True, YELLOW),    (sx + 65, 122))

    combo_col = (80, 220, 255) if combo >= 2 else tuple(max(c - 110, 0) for c in BORDER_COLOR)
    combo_str = f"COMBO  ×{combo}" if combo >= 2 else "COMBO"
    surf.blit(_font(11).render(combo_str, True, combo_col), (sx, 142))

    surf.blit(_font(12).render("SPEED", True, BORDER_COLOR), (sx, 168))
    surf.blit(_font(17).render(f"T{speed_tier}", True, YELLOW), (sx, 182))
    if reset_bonus_mult > 1.005:
        surf.blit(_font(12).render(f"×{reset_bonus_mult:.1f}", True, (255, 200, 50)),
                  (sx + 48, 185))

    surf.blit(_font(12).render("FULL CASCADE IN", True, BORDER_COLOR), (sx, 207))
    pts_left = max(0, next_speed_reset - score)
    if pts_left > 2000:
        rst_col = (100, 255, 100)
    elif pts_left > 500:
        rst_col = (255, 200, 50)
    else:
        rst_col = (255, 80, 80)
    surf.blit(_font(14).render(f"{pts_left:,} pts", True, rst_col), (sx, 220))

    box_w  = SIDEBAR_WIDTH - 16
    box_x  = sx - 4
    mini   = CELL_SIZE - 8
    tiny   = 10

    NEXT_Y     = 242
    NEXT_BOX_Y = NEXT_Y + 20
    P1_H       = 72
    MINI_H     = 78
    NEXT_BOX_H = P1_H + 2 + MINI_H

    surf.blit(_font(13).render("NEXT", True, BORDER_COLOR), (sx, NEXT_Y))

    if next_flash_timer > 0:
        fa = min(1.0, next_flash_timer / 120)
        fc = tuple(int(c * fa) for c in (255, 255, 255))
        pygame.draw.rect(surf, fc,
                         (box_x - 1, NEXT_BOX_Y - 1, box_w + 2, NEXT_BOX_H + 2), 2,
                         border_radius=3)
    pygame.draw.rect(surf, BORDER_COLOR, (box_x, NEXT_BOX_Y, box_w, NEXT_BOX_H), 1)

    p1 = piece_queue[0] if piece_queue else None
    if p1 is not None:
        s1 = p1.shape
        pc = max(len(r) for r in s1);  pr = len(s1)
        ox = box_x + (box_w - pc * (mini + 1)) // 2
        oy = NEXT_BOX_Y + (P1_H - pr * (mini + 1)) // 2
        for ri, row in enumerate(s1):
            for ci, v in enumerate(row):
                if v:
                    surf.blit(get_block(v, mini, palette_phase=palette_phase),
                              (ox + ci * (mini + 1), oy + ri * (mini + 1)))

    div_y = NEXT_BOX_Y + P1_H + 1
    pygame.draw.line(surf, tuple(max(c - 60, 0) for c in BORDER_COLOR),
                     (box_x + 4, div_y), (box_x + box_w - 4, div_y))

    half_w   = box_w // 2
    grid_y   = div_y + 3
    slot_h   = (MINI_H - 4) // 2
    for idx in range(4):
        p = piece_queue[idx + 1] if (idx + 1) < len(piece_queue) else None
        col_i = idx % 2;  row_i = idx // 2
        slot_x = box_x + col_i * half_w
        slot_y = grid_y + row_i * slot_h
        if col_i == 0:
            pygame.draw.line(surf, tuple(max(c - 60, 0) for c in BORDER_COLOR),
                             (box_x + half_w, grid_y + 2),
                             (box_x + half_w, grid_y + MINI_H - 5))
        if p is not None:
            sp = p.shape
            pc2 = max(len(r) for r in sp);  pr2 = len(sp)
            ox2 = slot_x + (half_w - pc2 * (tiny + 1)) // 2
            oy2 = slot_y + (slot_h - pr2 * (tiny + 1)) // 2
            for ri, row in enumerate(sp):
                for ci, v in enumerate(row):
                    if v:
                        surf.blit(get_block(v, tiny, palette_phase=palette_phase),
                                  (ox2 + ci * (tiny + 1), oy2 + ri * (tiny + 1)))

    HOLD_Y     = NEXT_BOX_Y + NEXT_BOX_H + 12
    HOLD_BOX_Y = HOLD_Y + 20
    HOLD_BOX_H = 66

    surf.blit(_font(13).render("HOLD", True, BORDER_COLOR), (sx, HOLD_Y))
    if hold_has_piece:
        t_ms = pygame.time.get_ticks()
        glow = 0.45 + 0.45 * math.sin(t_ms / 285.0)
        gc   = tuple(int(c * glow) for c in (80, 220, 255))
        pygame.draw.rect(surf, gc,
                         (box_x - 1, HOLD_BOX_Y - 1, box_w + 2, HOLD_BOX_H + 2), 2,
                         border_radius=3)
    border_col = tuple(max(c - 80, 0) for c in BORDER_COLOR) if hold_used else BORDER_COLOR
    pygame.draw.rect(surf, border_col, (box_x, HOLD_BOX_Y, box_w, HOLD_BOX_H), 1)
    if hold_piece is not None:
        sh = hold_piece.shape
        pc = max(len(r) for r in sh);  pr = len(sh)
        ox = box_x + (box_w - pc * (mini + 1)) // 2
        oy = HOLD_BOX_Y + (HOLD_BOX_H - pr * (mini + 1)) // 2
        for ri, row in enumerate(sh):
            for ci, v in enumerate(row):
                if v:
                    blk = get_block(v, mini, palette_phase=palette_phase)
                    if hold_used:
                        blk = blk.copy(); blk.set_alpha(90)
                    surf.blit(blk, (ox + ci * (mini + 1), oy + ri * (mini + 1)))

    ctrl_y = HOLD_BOX_Y + HOLD_BOX_H + 10
    for i, h in enumerate(["<> move  ^ rot  Z ccw",
                            "v drop  SPC hard  C hold"]):
        surf.blit(_font(10).render(h, True, BORDER_COLOR), (sx, ctrl_y + i * 14))

    draw_popup(surf, popup_count, popup_timer)


# ── game-over overlay ─────────────────────────────────────────────────────────

def draw_game_over_overlay(surf: pygame.Surface, score: int,
                           stat_pieces: int = 0, stat_tetrises: int = 0,
                           stat_tspins: int = 0, stat_combo: int = 0,
                           stat_time: float = 0.0) -> None:
    ov = pygame.Surface((BOARD_WIDTH, 220), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 210))
    surf.blit(ov, (0, BOARD_HEIGHT // 2 - 50))
    cx = BOARD_WIDTH // 2

    t = _font(26).render("GAME OVER", True, (255, 60, 60))
    surf.blit(t, (cx - t.get_width() // 2, BOARD_HEIGHT // 2 - 44))

    t = _font(17).render(f"SCORE  {str(score).zfill(7)}", True, YELLOW)
    surf.blit(t, (cx - t.get_width() // 2, BOARD_HEIGHT // 2 - 8))

    mins, secs = divmod(int(stat_time), 60)
    time_str   = f"{mins}:{secs:02d}"
    stats = [
        ("TIME",     time_str),
        ("PIECES",   str(stat_pieces)),
        ("TETRISES", str(stat_tetrises)),
        ("T-SPINS",  str(stat_tspins)),
        ("BEST COMBO", f"×{stat_combo}"),
    ]
    sy = BOARD_HEIGHT // 2 + 18
    for label, val in stats:
        tl = _font(11, bold=False).render(label, True, BORDER_COLOR)
        tv = _font(12).render(val, True, (200, 220, 255))
        surf.blit(tl, (cx - 70, sy))
        surf.blit(tv, (cx + 20, sy))
        sy += 16

    for i, hint in enumerate(["SPACE / ESC = menu",
                               "L = leaderboard"]):
        t = _font(12, bold=False).render(hint, True, BORDER_COLOR)
        surf.blit(t, (cx - t.get_width() // 2, sy + 6 + i * 15))


# ── settings ─────────────────────────────────────────────────────────────────

def draw_settings(surf: pygame.Surface, music_vol: int, sfx_vol: int,
                  settings_row: int, muted: bool, scale: float,
                  ghost_opacity: int = 25, das_preset: str = "normal") -> None:
    surf.fill(BG_COLOR)
    cx = SCREEN_WIDTH // 2

    t = _font(30).render("SETTINGS", True, YELLOW)
    surf.blit(t, (cx - t.get_width() // 2, 26))
    pygame.draw.line(surf, BORDER_COLOR, (40, 68), (SCREEN_WIDTH - 40, 68), 1)

    def _vol_row(label, pct, y, selected):
        col = YELLOW if selected else BORDER_COLOR
        surf.blit(_font(14, bold=False).render(label, True, col), (60, y))
        bx, by, bw, bh = 60, y + 22, 200, 13
        pygame.draw.rect(surf, BORDER_COLOR, (bx, by, bw, bh), 1)
        fill_w = int(bw * pct / 100)
        if fill_w > 2:
            pygame.draw.rect(surf, col, (bx + 1, by + 1, fill_w - 2, bh - 2))
        surf.blit(_font(14).render(f"{pct}%", True, col), (bx + bw + 10, by - 2))
        if selected:
            surf.blit(_font(11, bold=False).render("< / >  adjust", True, YELLOW),
                      (bx + bw + 10, by + 13))

    _vol_row("MUSIC VOLUME",  music_vol,    80, settings_row == 0)
    _vol_row("SFX VOLUME",    sfx_vol,      150, settings_row == 1)

    scale_col = YELLOW if settings_row == 2 else BORDER_COLOR
    surf.blit(_font(14, bold=False).render("DISPLAY SCALE", True, scale_col), (60, 222))
    for i, v in enumerate(config.VALID_SCALES):
        lbl    = f"{v:g}×"
        active = (v == scale)
        box_x  = 60 + i * 80
        box_col = YELLOW if (active and settings_row == 2) else (
                  BORDER_COLOR if not active else (210, 210, 80))
        pygame.draw.rect(surf, box_col, (box_x, 244, 68, 22), 0 if active else 1)
        tc = BG_COLOR if active else box_col
        surf.blit(_font(14).render(lbl, True, tc),
                  (box_x + 34 - _font(14).size(lbl)[0] // 2, 246))
    if settings_row == 2:
        surf.blit(_font(11, bold=False).render("< / >  change scale  (restarts window)",
                                               True, YELLOW), (60, 272))

    _vol_row("GHOST  OPACITY", ghost_opacity, 300, settings_row == 3)
    if settings_row == 3 and ghost_opacity == 0:
        surf.blit(_font(11, bold=False).render("shadow disabled", True, BORDER_COLOR),
                  (60, 336))
    elif settings_row == 3 and ghost_opacity == 100:
        surf.blit(_font(11, bold=False).render("full solid tile", True, BORDER_COLOR),
                  (60, 336))

    das_col = YELLOW if settings_row == 4 else BORDER_COLOR
    surf.blit(_font(14, bold=False).render("INPUT SPEED  (DAS / ARR)", True, das_col),
              (60, 348))
    das_labels = {"slow": "Slow", "normal": "Normal", "fast": "Fast", "instant": "Instant"}
    for i, key in enumerate(config.VALID_DAS_PRESETS):
        active  = (key == das_preset)
        box_col = YELLOW if (active and settings_row == 4) else (
                  BORDER_COLOR if not active else (210, 210, 80))
        bx = 60 + i * 98
        pygame.draw.rect(surf, box_col, (bx, 370, 86, 22), 0 if active else 1)
        tc  = BG_COLOR if active else box_col
        lbl = das_labels[key]
        surf.blit(_font(13).render(lbl, True, tc),
                  (bx + 43 - _font(13).size(lbl)[0] // 2, 372))
    if settings_row == 4:
        d, r = config.DAS_SETTINGS[das_preset]
        arr_str = "instant" if r == 0 else f"{r} ms"
        surf.blit(_font(11, bold=False).render(
            f"delay {d} ms  ·  repeat {arr_str}", True, YELLOW), (60, 398))

    mute_col = (255, 80, 80) if muted else (80, 220, 100)
    t = _font(15).render(f"M  —  MUSIC : {'MUTED' if muted else 'ON'}", True, mute_col)
    surf.blit(t, (cx - t.get_width() // 2, 424))

    pygame.draw.line(surf, BORDER_COLOR, (40, 452), (SCREEN_WIDTH - 40, 452), 1)
    for i, hint in enumerate(["UP / DOWN  :  select row",
                               "LEFT / RIGHT  :  adjust",
                               "ENTER / ESC  :  back to menu"]):
        t = _font(13, bold=False).render(hint, True, BORDER_COLOR)
        surf.blit(t, (cx - t.get_width() // 2, 466 + i * 20))

    pygame.draw.rect(surf, BORDER_COLOR, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 2)


# ── pause overlay ─────────────────────────────────────────────────────────────

def draw_pause(surf: pygame.Surface, blink_on: bool) -> None:
    ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 175))
    surf.blit(ov, (0, 0))

    if blink_on:
        word   = "PAUSE"
        total  = len(word) * 5 * _PAUSE_CELL + (len(word) - 1) * 8
        start_x = (SCREEN_WIDTH - total) // 2
        top_y   = 240
        for li, ch in enumerate(word):
            lx   = start_x + li * (5 * _PAUSE_CELL + 8)
            col  = _PAUSE_COLORS[li]
            glyph = _PAUSE_GLYPHS[ch]
            for gy in range(5):
                for gx in range(5):
                    if glyph[gy][gx]:
                        x = lx + gx * _PAUSE_CELL
                        y = top_y + gy * _PAUSE_CELL
                        pygame.draw.rect(surf, col,
                                         (x, y, _PAUSE_BLOCK, _PAUSE_BLOCK))
                        bright = tuple(min(255, c + 90) for c in col)
                        pygame.draw.line(surf, bright,
                                         (x, y), (x + _PAUSE_BLOCK - 1, y))
                        pygame.draw.line(surf, bright,
                                         (x, y), (x, y + _PAUSE_BLOCK - 1))
                        dark = tuple(max(0, c - 60) for c in col)
                        pygame.draw.line(surf, dark,
                                         (x + _PAUSE_BLOCK - 1, y),
                                         (x + _PAUSE_BLOCK - 1, y + _PAUSE_BLOCK - 1))
                        pygame.draw.line(surf, dark,
                                         (x, y + _PAUSE_BLOCK - 1),
                                         (x + _PAUSE_BLOCK - 1, y + _PAUSE_BLOCK - 1))

    cx = SCREEN_WIDTH // 2
    t = _font(15).render("PRESS  SPACE  TO  RESUME", True, WHITE)
    surf.blit(t, (cx - t.get_width() // 2, 332))
    t = _font(12, bold=False).render("S  —  settings    Q  —  exit to menu", True, BORDER_COLOR)
    surf.blit(t, (cx - t.get_width() // 2, 356))


# ── music preview ─────────────────────────────────────────────────────────────

def draw_music_test(surf: pygame.Surface, selected: int) -> None:
    surf.fill(BG_COLOR)
    cx = SCREEN_WIDTH // 2

    t = _font(22).render("MUSIC  PREVIEW", True, YELLOW)
    surf.blit(t, (cx - t.get_width() // 2, 20))
    pygame.draw.line(surf, BORDER_COLOR, (40, 54), (SCREEN_WIDTH - 40, 54), 1)

    hint = _font(11, bold=False).render(
        "UP / DOWN : select tier     ESC : back to menu", True, BORDER_COLOR)
    surf.blit(hint, (cx - hint.get_width() // 2, 60))
    pygame.draw.line(surf, BORDER_COLOR, (40, 78), (SCREEN_WIDTH - 40, 78), 1)

    ROW_H = 42
    for i in range(1, 11):
        y   = 86 + (i - 1) * ROW_H
        sel = (i == selected)
        col = YELLOW if sel else BORDER_COLOR
        if sel:
            pygame.draw.polygon(surf, YELLOW,
                                [(46, y + 8), (54, y + 13), (46, y + 18)])
        surf.blit(_font(16).render(f"TIER {i:>2}", True, col), (62, y + 4))
        desc_col = BORDER_COLOR if not sel else (220, 220, 100)
        surf.blit(_font(12, bold=False).render(_TIER_DESC[i], True, desc_col),
                  (158, y + 7))
        if sel:
            pygame.draw.line(surf, YELLOW,
                             (62, y + ROW_H - 4), (SCREEN_WIDTH - 40, y + ROW_H - 4), 1)

    pygame.draw.rect(surf, BORDER_COLOR, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 2)


# ── menu ──────────────────────────────────────────────────────────────────────

def _draw_mini_piece(surf, shape, cx, cy, cell):
    cols = max(len(r) for r in shape)
    rows = len(shape)
    ox   = cx - cols * (cell + 1) // 2
    oy   = cy - rows * (cell + 1) // 2
    for ri, row in enumerate(shape):
        for ci, val in enumerate(row):
            if val:
                surf.blit(get_block(val, cell),
                          (ox + ci * (cell + 1), oy + ri * (cell + 1)))


def draw_menu(surf: pygame.Surface, blink_on: bool) -> None:
    surf.fill(BG_COLOR)
    cx = SCREEN_WIDTH // 2

    letters = list("T3TR1S")
    widths  = [_font(56).size(l)[0] for l in letters]
    x = cx - sum(widths) // 2
    for letter, color in zip(letters, _TITLE_COLORS):
        t = _font(56).render(letter, True, color)
        surf.blit(t, (x, 58)); x += t.get_width()

    pygame.draw.line(surf, BORDER_COLOR, (cx - 160, 130), (cx + 160, 130), 1)
    t = _font(12, bold=False).render("by kakoritz", True, BORDER_COLOR)
    surf.blit(t, (cx - t.get_width() // 2, 135))
    pygame.draw.line(surf, BORDER_COLOR, (cx - 160, 153), (cx + 160, 153), 1)

    slot_w = SCREEN_WIDTH // len(SHAPES)
    for i, pt in enumerate(SHAPES):
        _draw_mini_piece(surf, SHAPES[pt], slot_w * i + slot_w // 2, 218, 16)

    if blink_on:
        t = _font(17).render("PRESS  SPACE  TO  START", True, WHITE)
        surf.blit(t, (cx - t.get_width() // 2, 288))

    for i, line in enumerate(["<  >  move       ^ rotate CW",
                               "Z rotate CCW     v  soft drop",
                               "SPACE hard drop",
                               "S  settings      M  mute",
                               "T  music preview"]):
        t = _font(12, bold=False).render(line, True, BORDER_COLOR)
        surf.blit(t, (cx - t.get_width() // 2, 358 + i * 18))

    pygame.draw.rect(surf, BORDER_COLOR, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 2)


# ── name entry ────────────────────────────────────────────────────────────────

def draw_name_entry(surf: pygame.Surface, initials: list, cursor: int,
                    blink_on: bool, score: int, lines: int, level: int) -> None:
    surf.fill(BG_COLOR)
    cx = SCREEN_WIDTH // 2

    t = _font(30).render("NEW HIGH SCORE!", True, YELLOW)
    surf.blit(t, (cx - t.get_width() // 2, 70))

    t = _font(19).render(f"SCORE  {str(score).zfill(7)}", True, WHITE)
    surf.blit(t, (cx - t.get_width() // 2, 118))

    t = _font(14, bold=False).render(f"LINES {lines}    LEVEL {level}", True, BORDER_COLOR)
    surf.blit(t, (cx - t.get_width() // 2, 148))

    pygame.draw.line(surf, BORDER_COLOR, (cx - 140, 174), (cx + 140, 174), 1)

    t = _font(14, bold=False).render("ENTER YOUR INITIALS", True, BORDER_COLOR)
    surf.blit(t, (cx - t.get_width() // 2, 188))

    slot, gap = 58, 18
    sx = cx - (3 * slot + 2 * gap) // 2
    for i, ch in enumerate(initials):
        x      = sx + i * (slot + gap)
        active = (i == cursor)
        pygame.draw.rect(surf, YELLOW if active else BORDER_COLOR,
                         (x, 218, slot, slot), 2)
        if (not active) or blink_on:
            t = _font(40).render(ch, True, YELLOW if active else WHITE)
            surf.blit(t, (x + slot // 2 - t.get_width() // 2,
                          218 + slot // 2 - t.get_height() // 2))

    if blink_on:
        ax = sx + cursor * (slot + gap) + slot // 2
        t  = _font(14, bold=False).render("^", True, YELLOW)
        surf.blit(t, (ax - t.get_width() // 2, 284))

    for i, hint in enumerate(["UP / DOWN : change letter",
                               "LEFT / RIGHT : move cursor",
                               "ENTER : confirm"]):
        t = _font(14, bold=False).render(hint, True, BORDER_COLOR)
        surf.blit(t, (cx - t.get_width() // 2, 322 + i * 20))

    pygame.draw.rect(surf, BORDER_COLOR, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 2)


# ── leaderboard ───────────────────────────────────────────────────────────────

def draw_leaderboard(surf: pygame.Surface, scores: list,
                     hi_name: str | None, hi_score: int | None) -> None:
    surf.fill(BG_COLOR)
    cx = SCREEN_WIDTH // 2

    t = _font(26).render("HIGH  SCORES", True, YELLOW)
    surf.blit(t, (cx - t.get_width() // 2, 28))

    pygame.draw.line(surf, BORDER_COLOR, (30, 64), (SCREEN_WIDTH - 30, 64), 1)

    t = _font(13).render("  #  NAME    SCORE   LINES  LVL", True, BORDER_COLOR)
    surf.blit(t, (30, 72))
    pygame.draw.line(surf, BORDER_COLOR, (30, 88), (SCREEN_WIDTH - 30, 88), 1)

    for i, e in enumerate(scores):
        is_new = (e["name"] == hi_name and e["score"] == hi_score)
        row = (f"  {i+1:<2}  {e['name']:<4}  "
               f"{str(e['score']).zfill(7)}  "
               f"{e['lines']:>5}  {e['level']:>3}")
        t = _font(15).render(row, True, YELLOW if is_new else WHITE)
        surf.blit(t, (30, 98 + i * 26))

    pygame.draw.line(surf, BORDER_COLOR,
                     (30, SCREEN_HEIGHT - 56), (SCREEN_WIDTH - 30, SCREEN_HEIGHT - 56), 1)
    for i, hint in enumerate(["ENTER / ESC : menu", "R : play again"]):
        t = _font(13, bold=False).render(hint, True, BORDER_COLOR)
        surf.blit(t, (cx - t.get_width() // 2, SCREEN_HEIGHT - 46 + i * 18))

    pygame.draw.rect(surf, BORDER_COLOR, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 2)
