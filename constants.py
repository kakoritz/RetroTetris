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

# NES-style fall speed per level (milliseconds per row)
def fall_speed(level: int) -> int:
    return max(80, 500 - (level - 1) * 45)

# NES scoring: multiplier * (level + 1)
SCORE_TABLE = {1: 40, 2: 100, 3: 300, 4: 1200}
