"""
renderer_mobile.py — Android full-screen layout for RETRIS.

Canvas: SCREEN_WIDTH × M_CANVAS_H  (460 × 940 logical pixels)

  y=0  ┌──────────────────────────────────────────────┐
       │  Stats strip  (M_STATS_H = 70 px)            │
  y=70 ├──────────────────────────────────────────────┤
       │                                              │
       │  Game board  (M_BOARD_W × M_BOARD_H)         │
       │  400 × 800, CELL=40, 30 px margins L/R       │
       │                                              │
 y=870 ├──────────────────────────────────────────────┤
       │  Touch controls  (M_BTN_H = 70 px, 6 btns)  │
 y=940 └──────────────────────────────────────────────┘

Scale from desktop (CELL_SIZE=30): multiply x/y by _CELL_SCALE (4/3).
"""
import pygame
import math
import colorsys

from constants import (
    LEVEL_THEMES, SCREEN_WIDTH, CELL_SIZE, BOARD_WIDTH,
    BG_COLOR, BORDER_COLOR, WHITE, YELLOW,
)
from sprites import get_block, get_ghost
from renderer import _font, _draw_block_icon, _TC_ICONS, draw_odometer
from game_constants import (
    FLASH_COLOR_NORM, FLASH_COLOR_QUAD,
    WOW_POPUP_DURATION, POPUP_DURATION, POPUP_STYLES,
)

# ── mobile geometry ────────────────────────────────────────────────────────────
M_CELL     = 40
M_BOARD_W  = 10 * M_CELL                           # 400
M_BOARD_H  = 20 * M_CELL                           # 800
M_STATS_H  = 70
M_BTN_H    = 70
M_BOARD_X  = (SCREEN_WIDTH - M_BOARD_W) // 2      # 30
M_BOARD_Y  = M_STATS_H                             # 70
M_CANVAS_H = M_STATS_H + M_BOARD_H + M_BTN_H      # 940

_CELL_SCALE = M_CELL / CELL_SIZE                   # 4/3

# Pause button hitbox in the stats strip (top-right corner)
M_PAUSE_RECT = pygame.Rect(SCREEN_WIDTH - 42, 4, 38, M_STATS_H - 8)

# ── touch button layout (6 buttons, no pause) ──────────────────────────────────
_M_N         = 6
_M_ICON_KEYS = ['left', 'down', 'drop', 'hold', 'rotate', 'right']
_M_COLOR_IDS = [1, 4, 6, 2, 3, 1]
_M_LABELS    = ['LEFT', 'DOWN', 'DROP', 'HOLD', 'ROTATE', 'RIGHT']

# ── colour palette ─────────────────────────────────────────────────────────────
_BG_STRIP   = (6,  6,  18)
_BTN_BG     = (10, 10, 26)
_PRESS_BG   = (30, 30, 58)
_BTN_BORDER = (55, 58, 105)
_DIV_COL    = (38, 38, 66)
_LBL_COL    = (85, 88, 135)
_HOLD_DIM   = 80   # alpha for used hold piece


# ── board ──────────────────────────────────────────────────────────────────────

def draw_mobile_board(surf: pygame.Surface, board,
                      flash_rows=None, flash_on: bool = False,
                      flash_quad: bool = False, wow_on: bool = False,
                      palette_phase: int = 0) -> None:
    """Draw the board grid onto surf (should be M_BOARD_W × M_BOARD_H)."""
    theme      = LEVEL_THEMES[palette_phase % len(LEVEL_THEMES)]
    board_cell = theme[0]
    grid_line  = theme[1]
    surf.fill(grid_line)

    if wow_on and flash_on:
        h = (pygame.time.get_ticks() / 90) % 1.0
        r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
        fc = (int(r * 255), int(g * 255), int(b * 255))
    elif flash_quad:
        fc = FLASH_COLOR_QUAD
    else:
        fc = FLASH_COLOR_NORM

    for gy, row in enumerate(board.grid):
        for gx, val in enumerate(row):
            px = gx * M_CELL
            py = gy * M_CELL
            if wow_on and flash_on:
                pygame.draw.rect(surf, fc, (px, py, M_CELL - 1, M_CELL - 1))
            elif flash_rows and gy in flash_rows and flash_on:
                pygame.draw.rect(surf, fc, (px, py, M_CELL - 1, M_CELL - 1))
            elif val:
                surf.blit(get_block(val, M_CELL, palette_phase=palette_phase), (px, py))
            else:
                pygame.draw.rect(surf, board_cell, (px, py, M_CELL - 1, M_CELL - 1))


def draw_mobile_danger_line(surf: pygame.Surface) -> None:
    y = 10 * M_CELL
    t = pygame.time.get_ticks()
    pulse = 0.5 + 0.5 * math.sin(t * 0.016)
    gb    = int(20 + 30 * pulse)
    col   = (255, gb, gb)
    pygame.draw.line(surf, col,  (0, y),     (M_BOARD_W - 1, y),     2)
    glow = (int(255 * 0.28), int(gb * 0.28), int(gb * 0.28))
    pygame.draw.line(surf, glow, (0, y - 1), (M_BOARD_W - 1, y - 1), 1)
    pygame.draw.line(surf, glow, (0, y + 2), (M_BOARD_W - 1, y + 2), 1)


def draw_mobile_piece(surf: pygame.Surface, piece,
                      palette_phase: int = 0) -> None:
    for row_i, row in enumerate(piece.shape):
        for col_i, val in enumerate(row):
            if val:
                surf.blit(get_block(val, M_CELL, palette_phase=palette_phase),
                          ((piece.x + col_i) * M_CELL,
                           (piece.y + row_i) * M_CELL))


def draw_mobile_ghost(surf: pygame.Surface, board, piece,
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
                                    palette_phase=palette_phase,
                                    size=M_CELL),
                          ((piece.x + col_i) * M_CELL,
                           (gy + row_i) * M_CELL))


# ── popup (board-space) ────────────────────────────────────────────────────────

def draw_mobile_popup(surf: pygame.Surface, count: int, timer: int) -> None:
    """Like draw_popup but positions relative to M_BOARD_W / M_BOARD_H."""
    if timer <= 0 or count not in POPUP_STYLES:
        return
    text_str, base_color, base_size = POPUP_STYLES[count]

    is_wow   = (count in (0, 13, 15))
    duration = WOW_POPUP_DURATION if is_wow else POPUP_DURATION
    elapsed  = duration - timer

    if is_wow:
        y = M_BOARD_H // 2 - 18 - int((elapsed / duration) * 60)
    else:
        start_y = int(M_BOARD_H * 0.62)
        y = start_y - int((elapsed / POPUP_DURATION) * 80)

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
    tw, _th = f.size(text_str)

    pad_x = 14 if is_wow else 10
    pad_y = 7  if is_wow else 4
    bw, bh = tw + pad_x * 2, _th + pad_y * 2
    bx = M_BOARD_W // 2 - bw // 2
    bg_a = 0.30 if is_wow else 0.22
    bg   = tuple(int(c * bg_a * alpha) for c in vivid)
    pygame.draw.rect(surf, bg, (bx, y - pad_y, bw, bh), border_radius=6)
    shadow = tuple(int(c * 0.25 * alpha) for c in vivid)
    t = f.render(text_str, True, shadow)
    surf.blit(t, (M_BOARD_W // 2 - tw // 2 + 2, y + 2))
    t = f.render(text_str, True, color)
    surf.blit(t, (M_BOARD_W // 2 - tw // 2, y))


# ── level-up overlay ───────────────────────────────────────────────────────────

def draw_mobile_level_up(surf: pygame.Surface, level_num: int,
                         timer: int, max_timer: int,
                         palette_phase: int = 0) -> None:
    """Full-board LEVEL N overlay drawn onto the board surface."""
    if timer <= 0 or max_timer <= 0:
        return
    prog  = timer / max_timer
    alpha = min(1.0, 2.0 * min(prog, 1.0 - prog) / 0.5 + 0.05)
    alpha = max(0.0, min(1.0, alpha))

    theme = LEVEL_THEMES[palette_phase % len(LEVEL_THEMES)]
    gc    = theme[1]
    bc    = tuple(min(255, int(c * 4)) for c in gc)
    ov    = pygame.Surface((M_BOARD_W, M_BOARD_H), pygame.SRCALPHA)
    ov.fill((*BG_COLOR, int(190 * alpha)))
    surf.blit(ov, (0, 0))

    txt   = f"LEVEL {level_num}"
    size  = 38
    f     = _font(size)
    tw, th = f.size(txt)
    cx    = M_BOARD_W // 2
    cy    = M_BOARD_H // 2

    shadow_col = tuple(int(c * 0.3 * alpha) for c in bc)
    t = f.render(txt, True, shadow_col)
    surf.blit(t, (cx - tw // 2 + 3, cy - th // 2 + 3))
    t = f.render(txt, True, tuple(int(c * alpha) for c in bc))
    surf.blit(t, (cx - tw // 2, cy - th // 2))


# ── stats strip ───────────────────────────────────────────────────────────────

def _draw_mini_piece(surf: pygame.Surface, piece, cell: int,
                     cx: int, cy: int,
                     dimmed: bool = False,
                     palette_phase: int = 0) -> None:
    """Render a piece centred at (cx, cy) using mini blocks of `cell` px."""
    if piece is None:
        return
    sh = piece.shape
    pc = max(len(r) for r in sh)
    pr = len(sh)
    ox = cx - pc * cell // 2
    oy = cy - pr * cell // 2
    for ri, row in enumerate(sh):
        for ci, v in enumerate(row):
            if v:
                blk = get_block(v, cell, palette_phase=palette_phase)
                if dimmed:
                    blk = blk.copy()
                    blk.set_alpha(_HOLD_DIM)
                surf.blit(blk, (ox + ci * cell, oy + ri * cell))


def draw_mobile_stats(surf: pygame.Surface,
                      score: int, lines: int, level: int,
                      piece_queue: list, best: int,
                      hold_piece=None, hold_used: bool = False,
                      score_digits: list | None = None,
                      score_anim_from: list | None = None,
                      score_anim_offs: list | None = None,
                      palette_phase: int = 0,
                      hold_has_piece: bool = False,
                      in_game: bool = False) -> None:
    """Draw the 460×M_STATS_H horizontal stats strip at the top of the canvas."""
    # Background
    pygame.draw.rect(surf, _BG_STRIP, (0, 0, SCREEN_WIDTH, M_STATS_H))
    pygame.draw.line(surf, _BTN_BORDER, (0, M_STATS_H - 1), (SCREEN_WIDTH, M_STATS_H - 1), 1)

    cy = M_STATS_H // 2   # vertical centre of strip

    # ── HOLD piece (x: 0-68) ────────────────────────────────────────────────
    hold_box = pygame.Rect(2, 3, 64, M_STATS_H - 6)
    # Glow when a piece is queued
    if hold_has_piece:
        t_ms = pygame.time.get_ticks()
        glow = 0.45 + 0.45 * math.sin(t_ms / 285.0)
        gc   = tuple(int(c * glow) for c in (80, 220, 255))
        pygame.draw.rect(surf, gc, hold_box.inflate(2, 2), 2, border_radius=3)
    border_col = tuple(max(c - 80, 0) for c in BORDER_COLOR) if hold_used else BORDER_COLOR
    pygame.draw.rect(surf, border_col, hold_box, 1)
    surf.blit(_font(8).render("H", True, _LBL_COL), (6, 4))
    _draw_mini_piece(surf, hold_piece, 12,
                     hold_box.centerx, hold_box.centery,
                     dimmed=hold_used, palette_phase=palette_phase)

    # Divider
    pygame.draw.line(surf, _DIV_COL, (70, 6), (70, M_STATS_H - 6), 1)

    # ── LEVEL (x: 72-124) ───────────────────────────────────────────────────
    surf.blit(_font(9).render("LVL", True, _LBL_COL), (73, 4))
    lv_txt = _font(18).render(str(level), True, BORDER_COLOR)
    surf.blit(lv_txt, (73, 18))

    # ── LINES (x: 126-178) ──────────────────────────────────────────────────
    surf.blit(_font(9).render("LNS", True, _LBL_COL), (126, 4))
    ln_txt = _font(18).render(str(lines), True, BORDER_COLOR)
    surf.blit(ln_txt, (126, 18))

    pygame.draw.line(surf, _DIV_COL, (180, 6), (180, M_STATS_H - 6), 1)

    # ── SCORE (x: 182-330) ──────────────────────────────────────────────────
    surf.blit(_font(9).render("SCORE", True, _LBL_COL), (183, 4))
    if score_digits is not None and score_anim_from is not None and score_anim_offs is not None:
        draw_odometer(surf, score_digits, score_anim_from, score_anim_offs, 183, 17)
    else:
        sc_txt = _font(16).render(str(score).zfill(8), True, YELLOW)
        surf.blit(sc_txt, (183, 17))

    pygame.draw.line(surf, _DIV_COL, (333, 6), (333, M_STATS_H - 6), 1)

    # ── NEXT 2 pieces (x: 335-420) ──────────────────────────────────────────
    nxt_cell = 9   # mini cell size for next pieces
    nxt_slot = 42  # width per slot
    for idx in range(2):
        p = piece_queue[idx] if idx < len(piece_queue) else None
        _draw_mini_piece(surf, p, nxt_cell,
                         335 + nxt_slot * idx + nxt_slot // 2,
                         cy, palette_phase=palette_phase)

    # ── PAUSE button (x: 420-460) ────────────────────────────────────────────
    if in_game:
        r = M_PAUSE_RECT
        pygame.draw.rect(surf, _BTN_BG, r, border_radius=4)
        pygame.draw.rect(surf, _BTN_BORDER, r, 1, border_radius=4)
        t = _font(16).render("II", True, BORDER_COLOR)
        surf.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))


# ── touch controls ─────────────────────────────────────────────────────────────

def draw_mobile_touch_controls(surf: pygame.Surface,
                                zone_y: int, zone_h: int) -> None:
    """6-button touch strip with button-box appearance and press highlighting."""
    btn_w = SCREEN_WIDTH // _M_N   # 76 px each (last gets remainder)

    # Pressed button state
    try:
        import logic.touch_controls as _tc
        pressed = set(_tc._held.values())
    except Exception:
        pressed = set()

    cell      = max(7, min(btn_w // 7, zone_h // 8))   # icon block cell size
    cy_icon   = zone_y + int(zone_h * 0.42)
    label_sz  = max(8, zone_h // 9)
    cy_label  = zone_y + zone_h - label_sz - 4

    # Zone background
    pygame.draw.rect(surf, _BG_STRIP, (0, zone_y, SCREEN_WIDTH, zone_h))
    pygame.draw.line(surf, _BTN_BORDER, (0, zone_y), (SCREEN_WIDTH, zone_y), 1)

    for i in range(_M_N):
        x = btn_w * i
        w = btn_w if i < _M_N - 1 else SCREEN_WIDTH - btn_w * (_M_N - 1)
        cx = x + w // 2

        # Button box background
        box = pygame.Rect(x + 2, zone_y + 3, w - 4, zone_h - 6)
        bg  = _PRESS_BG if i in pressed else _BTN_BG
        pygame.draw.rect(surf, bg, box, border_radius=6)

        # Button border — brighter when pressed
        if i in pressed:
            bc = tuple(min(255, c + 50) for c in _BTN_BORDER)
        else:
            bc = _BTN_BORDER
        pygame.draw.rect(surf, bc, box, 1, border_radius=6)

        # Press highlight line at top of button
        if i in pressed:
            pygame.draw.line(surf, (100, 105, 170),
                             (x + 6, zone_y + 5), (x + w - 6, zone_y + 5), 1)

        # NES block-art icon
        icon_key = _M_ICON_KEYS[i]
        cid      = _M_COLOR_IDS[i]
        _draw_block_icon(surf, _TC_ICONS[icon_key], cid, cell, cx, cy_icon)

        # Label
        lbl = _font(label_sz).render(_M_LABELS[i], True, _LBL_COL)
        surf.blit(lbl, (cx - lbl.get_width() // 2, cy_label))
