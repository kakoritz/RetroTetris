import colorsys
import random
import pygame
import sys

import audio
audio.pre_init()

import highscore
import music
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


# ── states ────────────────────────────────────────────────────────────────────
MENU        = "menu"
PLAYING     = "playing"
CLEARING    = "clearing"
GAME_OVER   = "game_over"
ENTER_NAME  = "enter_name"
LEADERBOARD = "leaderboard"

_INITIALS_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ "

# ── DAS (delayed auto-shift) ──────────────────────────────────────────────────
DAS_DELAY  = 170   # ms before auto-repeat starts
DAS_REPEAT = 50    # ms between repeated moves

# ── line-clear flash animation ────────────────────────────────────────────────
FLASH_MS    = {1: 85, 2: 80, 3: 75, 4: 68}   # ms per on/off phase
FLASH_TOTAL = {1: 2,  2: 4,  3: 6,  4: 10}   # phases per count
FLASH_COLOR_NORM = (255, 255, 255)
FLASH_COLOR_QUAD = (255, 215,   0)

# ── sidebar popup ─────────────────────────────────────────────────────────────
POPUP_DURATION    = 2000   # ms
SHAKE_DURATION    = 380    # ms  (quad clear only)
SHAKE_INTENSITY   = 5      # px
HD_FLASH_DURATION = 90     # ms  (hard drop impact)

POPUP_STYLES = {
    1: ("Nice!",       (100, 255, 120), 17),
    2: ("Great!",      (255, 235,  60), 20),
    3: ("Fantastic!",  (255, 150,  50), 20),
    4: ("TETRIS!",      None,           24),   # None = rainbow
}

_font_cache: dict = {}

def _font(size: int, bold: bool = True) -> pygame.font.Font:
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont("monospace", size, bold=bold)
    return _font_cache[key]


# ── rotation helper ───────────────────────────────────────────────────────────

def _try_rotate(board: Board, piece: Piece, rot: list) -> bool:
    for dx in (0, 1, -1):
        if board.is_valid(piece, dx=dx, shape=rot):
            piece.x += dx
            piece.shape = rot
            audio.play('rotate')
            return True
    return False


# ── board / piece drawing ─────────────────────────────────────────────────────

def draw_board(surf: pygame.Surface, board: Board,
               flash_rows: set | None = None,
               flash_on: bool = False,
               flash_quad: bool = False) -> None:
    fc = FLASH_COLOR_QUAD if flash_quad else FLASH_COLOR_NORM
    for gy, row in enumerate(board.grid):
        for gx, val in enumerate(row):
            px, py = gx * CELL_SIZE, gy * CELL_SIZE
            if flash_rows and gy in flash_rows and flash_on:
                pygame.draw.rect(surf, fc, (px, py, CELL_SIZE - 1, CELL_SIZE - 1))
            elif val:
                surf.blit(get_block(val), (px, py))
            else:
                pygame.draw.rect(surf, GRID_COLOR,
                                 (px, py, CELL_SIZE - 1, CELL_SIZE - 1))


def draw_piece(surf: pygame.Surface, piece: Piece) -> None:
    for row_i, row in enumerate(piece.shape):
        for col_i, val in enumerate(row):
            if val:
                surf.blit(get_block(val),
                          ((piece.x + col_i) * CELL_SIZE,
                           (piece.y + row_i) * CELL_SIZE))


def draw_ghost(surf: pygame.Surface, board: Board, piece: Piece) -> None:
    gy = board.ghost_y(piece)
    if gy == piece.y:
        return
    for row_i, row in enumerate(piece.shape):
        for col_i, val in enumerate(row):
            if val:
                surf.blit(get_ghost(val),
                          ((piece.x + col_i) * CELL_SIZE,
                           (gy + row_i) * CELL_SIZE))


# ── popup ─────────────────────────────────────────────────────────────────────

def draw_popup(surf: pygame.Surface, count: int, timer: int) -> None:
    if timer <= 0 or count not in POPUP_STYLES:
        return
    text_str, base_color, base_size = POPUP_STYLES[count]
    elapsed = POPUP_DURATION - timer

    # Float upward over lifetime
    y = 440 - int((elapsed / POPUP_DURATION) * 22)

    # Fade out in last 500 ms
    alpha = 1.0 if timer > 500 else timer / 500

    # Pop: bigger font for the first 200 ms
    size = base_size + (5 if elapsed < 200 else 0)

    # Vivid color (before alpha applied)
    if base_color is None:   # rainbow for TETRIS
        h = (pygame.time.get_ticks() / 450) % 1.0
        r, g, b = colorsys.hsv_to_rgb(h, 0.9, 1.0)
        vivid = (int(r * 255), int(g * 255), int(b * 255))
    else:
        vivid = base_color

    color = tuple(int(c * alpha) for c in vivid)

    # Coloured background bar for count ≥ 2
    if count >= 2:
        f = _font(size)
        tw, th = f.size(text_str)
        pad_x, pad_y = 10, 4
        bw, bh = tw + pad_x * 2, th + pad_y * 2
        bx = BOARD_WIDTH + (SIDEBAR_WIDTH - bw) // 2
        bg = tuple(int(c * 0.22 * alpha) for c in vivid)
        pygame.draw.rect(surf, bg, (bx, y - pad_y, bw, bh), border_radius=4)

    t = _font(size).render(text_str, True, color)
    x = BOARD_WIDTH + (SIDEBAR_WIDTH - t.get_width()) // 2
    surf.blit(t, (x, y))


# ── sidebar ───────────────────────────────────────────────────────────────────

def draw_sidebar(surf: pygame.Surface, score: int, lines: int,
                 level: int, next_piece: Piece, best: int,
                 popup_count: int = 0, popup_timer: int = 0) -> None:
    sx = BOARD_WIDTH + 12

    def lbl(text, y): surf.blit(_font(13).render(text, True, BORDER_COLOR), (sx, y))
    def val(text, y): surf.blit(_font(19).render(text, True, YELLOW),       (sx, y))

    lbl("SCORE",  14); val(str(score).zfill(7),  30)
    lbl("BEST",   60); val(str(best).zfill(7),   76)
    lbl("LINES", 108); val(str(lines),           124)
    lbl("LEVEL", 155); val(str(level),           171)

    # NEXT piece box
    lbl("NEXT", 210)
    box_x, box_y = sx - 4, 228
    box_w, box_h = SIDEBAR_WIDTH - 16, 80
    pygame.draw.rect(surf, BORDER_COLOR, (box_x, box_y, box_w, box_h), 1)

    mini = CELL_SIZE - 6
    shape = next_piece.shape
    pc = max(len(r) for r in shape)
    pr = len(shape)
    ox = box_x + (box_w - pc * (mini + 1)) // 2
    oy = box_y + (box_h - pr * (mini + 1)) // 2
    for ri, row in enumerate(shape):
        for ci, v in enumerate(row):
            if v:
                surf.blit(get_block(v, mini),
                          (ox + ci * (mini + 1), oy + ri * (mini + 1)))

    # Controls hint
    for i, h in enumerate(["<>  move",
                            "^ cw   Z ccw",
                            "v  soft drop",
                            "SPC  hard drop"]):
        surf.blit(_font(11).render(h, True, BORDER_COLOR), (sx, 326 + i * 16))

    draw_popup(surf, popup_count, popup_timer)


# ── game-over overlay ─────────────────────────────────────────────────────────

def draw_game_over_overlay(surf: pygame.Surface, score: int) -> None:
    ov = pygame.Surface((BOARD_WIDTH, 120), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 200))
    surf.blit(ov, (0, BOARD_HEIGHT // 2 - 40))
    cx = BOARD_WIDTH // 2

    t = _font(26).render("GAME OVER", True, (255, 60, 60))
    surf.blit(t, (cx - t.get_width() // 2, BOARD_HEIGHT // 2 - 32))

    t = _font(17).render(f"SCORE  {str(score).zfill(7)}", True, YELLOW)
    surf.blit(t, (cx - t.get_width() // 2, BOARD_HEIGHT // 2 + 4))

    for i, hint in enumerate(["R = restart",
                               "ESC = menu",
                               "L = leaderboard"]):
        t = _font(13, bold=False).render(hint, True, BORDER_COLOR)
        surf.blit(t, (cx - t.get_width() // 2, BOARD_HEIGHT // 2 + 36 + i * 16))


# ── menu ──────────────────────────────────────────────────────────────────────

_TITLE_COLORS = [
    (160,   0, 240),
    (  0, 240, 240),
    (240, 240,   0),
    (  0, 240,   0),
    (  0,  60, 240),
    (240,   0,   0),
]


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

    t = _font(20).render("N  E  S", True, YELLOW)
    surf.blit(t, (cx - t.get_width() // 2, 68))

    letters = list("TETRIS")
    widths  = [_font(56).size(l)[0] for l in letters]
    x = cx - sum(widths) // 2
    for letter, color in zip(letters, _TITLE_COLORS):
        t = _font(56).render(letter, True, color)
        surf.blit(t, (x, 96)); x += t.get_width()

    pygame.draw.line(surf, BORDER_COLOR, (cx - 160, 164), (cx + 160, 164), 1)

    slot_w = SCREEN_WIDTH // len(SHAPES)
    for i, pt in enumerate(SHAPES):
        _draw_mini_piece(surf, SHAPES[pt], slot_w * i + slot_w // 2, 228, 16)

    if blink_on:
        t = _font(17).render("PRESS  ENTER  TO  START", True, WHITE)
        surf.blit(t, (cx - t.get_width() // 2, 298))

    for i, line in enumerate(["<  >  move       ^ rotate CW",
                               "Z rotate CCW     v  soft drop",
                               "SPACE hard drop"]):
        t = _font(12, bold=False).render(line, True, BORDER_COLOR)
        surf.blit(t, (cx - t.get_width() // 2, 368 + i * 18))

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


# ── game helper ───────────────────────────────────────────────────────────────

def new_game():
    return Board(), Piece(), Piece(), 0, 0, 1, 0


# ── main loop ─────────────────────────────────────────────────────────────────

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("NES TETRIS")
    clock = pygame.time.Clock()
    music.start()

    state = MENU
    board, current, next_piece, score, lines, level, fall_timer = new_game()
    best  = highscore.best()

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

    # name entry
    initials   = ['A', 'A', 'A']
    ini_cursor = 0

    # leaderboard
    lb_scores   = []
    lb_hi_name  = None
    lb_hi_score = None

    blink_timer  = 0
    blink_on     = True
    hard_dropped = False

    particles:      list = []
    shake_timer:    int  = 0
    hd_flash_timer: int  = 0
    clear_cells:    list = []

    def _spawn_next():
        nonlocal current, next_piece
        current    = next_piece
        next_piece = Piece()
        audio.play_spawn(current.color_id)
        return board.is_valid(current)

    def _end_game():
        """Decide whether to go to ENTER_NAME or GAME_OVER."""
        nonlocal state, initials, ini_cursor
        if highscore.qualifies(score):
            initials   = ['A', 'A', 'A']
            ini_cursor = 0
            state      = ENTER_NAME
        else:
            state = GAME_OVER

    def _reset_das():
        nonlocal das_dir, das_timer, das_charged
        das_dir = 0; das_timer = 0; das_charged = False; keys_held.clear()

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

            # ── MENU ──────────────────────────────────────────────────────────
            if state == MENU:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    board, current, next_piece, score, lines, level, fall_timer = new_game()
                    best  = highscore.best()
                    popup_count = popup_timer = 0
                    _reset_das()
                    audio.play_spawn(current.color_id)
                    state = PLAYING

            # ── PLAYING ───────────────────────────────────────────────────────
            elif state == PLAYING:
                if event.key == pygame.K_LEFT:
                    keys_held.add(pygame.K_LEFT)
                    das_dir = -1; das_timer = 0; das_charged = False
                    if board.is_valid(current, dx=-1):
                        current.x -= 1
                        audio.play('move')
                elif event.key == pygame.K_RIGHT:
                    keys_held.add(pygame.K_RIGHT)
                    das_dir = 1; das_timer = 0; das_charged = False
                    if board.is_valid(current, dx=1):
                        current.x += 1
                        audio.play('move')
                elif event.key == pygame.K_DOWN:
                    if board.is_valid(current, dy=1):
                        current.y += 1
                elif event.key == pygame.K_UP:
                    if event.mod & pygame.KMOD_CTRL:
                        _try_rotate(board, current, current.rotated_ccw())
                    else:
                        _try_rotate(board, current, current.rotated_cw())
                elif event.key == pygame.K_z:
                    _try_rotate(board, current, current.rotated_ccw())
                elif event.key == pygame.K_SPACE:
                    hard_dropped   = True
                    hd_flash_timer = HD_FLASH_DURATION
                    while board.is_valid(current, dy=1):
                        current.y += 1
                    audio.play('hard_drop')

            # ── GAME OVER ─────────────────────────────────────────────────────
            elif state == GAME_OVER:
                if event.key == pygame.K_r:
                    board, current, next_piece, score, lines, level, fall_timer = new_game()
                    popup_count = popup_timer = 0
                    _reset_das()
                    audio.play_spawn(current.color_id)
                    state = PLAYING
                elif event.key == pygame.K_ESCAPE:
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
                    state = MENU
                elif event.key == pygame.K_r:
                    board, current, next_piece, score, lines, level, fall_timer = new_game()
                    popup_count = popup_timer = 0
                    _reset_das()
                    audio.play_spawn(current.color_id)
                    state = PLAYING

        # ── DAS auto-repeat ───────────────────────────────────────────────────
        if state == PLAYING and das_dir != 0:
            das_timer += dt
            if not das_charged:
                if das_timer >= DAS_DELAY:
                    das_charged = True
                    das_timer   = 0
            else:
                while das_timer >= DAS_REPEAT:
                    das_timer -= DAS_REPEAT
                    if board.is_valid(current, dx=das_dir):
                        current.x += das_dir
                        audio.play('move')

        # ── gravity ───────────────────────────────────────────────────────────
        if state == PLAYING:
            fall_timer += dt
            if fall_timer >= fall_speed(level):
                fall_timer = 0
                if board.is_valid(current, dy=1):
                    current.y += 1
                else:
                    board.place(current)
                    if not hard_dropped:
                        audio.play('lock')
                    hard_dropped = False
                    _reset_das()
                    full = board.full_rows()
                    if full:
                        clear_rows      = set(full)
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
                        if _spawn_next():
                            pass   # continue playing
                        else:
                            _end_game()

        # ── line-clear animation ──────────────────────────────────────────────
        elif state == CLEARING:
            clear_timer += dt
            fms = FLASH_MS.get(clear_count, 80)
            if clear_timer >= fms:
                clear_timer -= fms
                clear_flash_idx += 1
                if clear_flash_idx >= FLASH_TOTAL.get(clear_count, 2):
                    # animation done — score, clear, spawn
                    lines  += clear_count
                    score  += SCORE_TABLE.get(clear_count, 0) * (level + 1)
                    level   = lines // 10 + 1
                    best    = max(best, score)
                    board.clear_lines()
                    particles += spawn_particles(clear_cells, clear_count == 4)
                    if clear_count == 4:
                        shake_timer = SHAKE_DURATION
                    popup_count = clear_count
                    popup_timer = POPUP_DURATION
                    if _spawn_next():
                        state = PLAYING
                    else:
                        _end_game()

        # ── popup / particle / fx timers ─────────────────────────────────────
        if popup_timer > 0:
            popup_timer = max(0, popup_timer - dt)
        particles      = update_particles(particles, dt)
        hd_flash_timer = max(0, hd_flash_timer - dt)
        shake_timer    = max(0, shake_timer    - dt)

        # ── draw ──────────────────────────────────────────────────────────────
        if state == MENU:
            draw_menu(screen, blink_on)

        elif state in (PLAYING, CLEARING, GAME_OVER):
            screen.fill(BG_COLOR)

            # Board content draws to its own surface so shake + flash can offset it
            bsurf = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))
            bsurf.fill(BG_COLOR)

            fr = clear_rows if state == CLEARING else None
            fo = (clear_flash_idx % 2 == 0) if state == CLEARING else False
            fq = (clear_count == 4) if state == CLEARING else False
            draw_board(bsurf, board, flash_rows=fr, flash_on=fo, flash_quad=fq)

            if state == PLAYING:
                draw_ghost(bsurf, board, current)
                draw_piece(bsurf, current)

            draw_particles(bsurf, particles)

            # Hard-drop white flash
            if hd_flash_timer > 0:
                alpha = int(190 * hd_flash_timer / HD_FLASH_DURATION)
                fl = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
                fl.fill((255, 255, 255, alpha))
                bsurf.blit(fl, (0, 0))

            if state == GAME_OVER:
                draw_game_over_overlay(bsurf, score)

            # Screen shake (quad only) — randomise offset each frame
            ox = oy = 0
            if shake_timer > 0:
                amt = max(1, int(SHAKE_INTENSITY * shake_timer / SHAKE_DURATION))
                ox  = random.randint(-amt, amt)
                oy  = random.randint(-amt, amt)

            screen.blit(bsurf, (ox, oy))

            draw_sidebar(screen, score, lines, level, next_piece, best,
                         popup_count, popup_timer)
            pygame.draw.rect(screen, BORDER_COLOR,
                             (0, 0, BOARD_WIDTH, BOARD_HEIGHT), 1)
            pygame.draw.line(screen, BORDER_COLOR,
                             (BOARD_WIDTH, 0), (BOARD_WIDTH, SCREEN_HEIGHT), 1)

        elif state == ENTER_NAME:
            draw_name_entry(screen, initials, ini_cursor, blink_on,
                            score, lines, level)

        elif state == LEADERBOARD:
            draw_leaderboard(screen, lb_scores, lb_hi_name, lb_hi_score)

        pygame.display.flip()


if __name__ == "__main__":
    main()
