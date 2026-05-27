"""
constants.py — geometry, palette, tetromino shapes, and fall-speed curve.

Imported by almost every module; has no project-level imports itself.
Changing COLS, ROWS, or CELL_SIZE ripples through board, renderer, and all
hit-test math — treat them as fixed for the lifetime of a run.
"""

COLS = 10
ROWS = 20
CELL_SIZE = 30

BOARD_WIDTH = COLS * CELL_SIZE    # 300
BOARD_HEIGHT = ROWS * CELL_SIZE   # 600
SIDEBAR_WIDTH = 160
SCREEN_WIDTH = BOARD_WIDTH + SIDEBAR_WIDTH   # 460
SCREEN_HEIGHT = BOARD_HEIGHT                 # 600

FPS = 60

# NES-inspired palette
BG_COLOR    = (15,  15,  35)
GRID_COLOR  = (30,  30,  60)
BORDER_COLOR = (185, 185, 220)
WHITE       = (255, 255, 255)
YELLOW      = (255, 220,  50)

# Color IDs for each tetromino (0 = empty)
COLORS = {
    0: GRID_COLOR,
    1: (  0, 240, 240),   # I  cyan
    2: (240, 240,   0),   # O  yellow
    3: (160,   0, 240),   # T  purple
    4: (  0, 240,   0),   # S  green
    5: (240,   0,   0),   # Z  red
    6: (  0,  60, 240),   # J  blue
    7: (240, 140,   0),   # L  orange
}

# Tetromino shapes — each cell stores its color ID
SHAPES = {
    'I': [[1, 1, 1, 1]],
    'O': [[2, 2],
          [2, 2]],
    'T': [[0, 3, 0],
          [3, 3, 3]],
    'S': [[0, 4, 4],
          [4, 4, 0]],
    'Z': [[5, 5, 0],
          [0, 5, 5]],
    'J': [[6, 0, 0],
          [6, 6, 6]],
    'L': [[0, 0, 7],
          [7, 7, 7]],
}

# NES-style fall speed: starts at 500 ms/row (level 1), drops 45 ms per level,
# floors at 80 ms/row (~level 10). Speed tier, not game level, is passed here.
def fall_speed(level: int) -> int:
    return max(80, 500 - (level - 1) * 45)

# NES scoring: multiplier * (level + 1)
SCORE_TABLE = {1: 40, 2: 100, 3: 300, 4: 1200}

# 10 level colour themes — one per level, cycling every 10 levels.
# Each entry: (board_cell, grid_line, tile_factor)
#   board_cell  — very-dark background fill for empty cells
#   grid_line   — 1-px separator visible between cells
#   tile_factor — brightness multiplier applied to all tile colours (≤1.0)
LEVEL_THEMES = [
    ((  5,   5,  18), (  0,  38,  65), 1.00),  #  1  Midnight Blue  (default)
    (( 12,   5,  20), ( 48,   0,  72), 0.92),  #  2  Deep Violet
    ((  5,  16,   5), (  0,  52,  20), 0.95),  #  3  Forest Deep
    ((  5,  14,  16), (  0,  44,  56), 0.93),  #  4  Abyssal Teal
    (( 20,   4,   4), ( 68,  10,  10), 0.90),  #  5  Crimson Void
    (( 20,  10,   2), ( 68,  32,   0), 0.94),  #  6  Ember
    (( 16,   4,  16), ( 58,   0,  58), 0.88),  #  7  Neon Magenta
    ((  4,  18,  10), (  8,  60,  30), 0.96),  #  8  Deep Emerald
    ((  5,   8,  22), ( 14,  22,  72), 0.97),  #  9  Cosmic Deep
    (( 20,  14,   2), ( 68,  46,   8), 0.91),  # 10  Solar Dusk
]
