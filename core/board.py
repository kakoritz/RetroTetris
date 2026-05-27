"""
board.py — 10×20 grid, collision detection, line clearing, and cascade gravity.

grid[row][col] stores the color_id of the placed block (0 = empty).
Row 0 is the top of the board; row ROWS-1 is the floor.
"""
from constants import COLS, ROWS
from piece import Piece


class Board:
    def __init__(self):
        self.grid: list[list[int]] = [[0] * COLS for _ in range(ROWS)]

    def is_valid(self, piece: Piece, dx: int = 0, dy: int = 0,
                 shape: list[list[int]] | None = None) -> bool:
        """Return True if the piece (optionally offset/rotated) fits on the board.

        dx/dy are trial offsets; shape overrides piece.shape for rotation tests.
        Cells above row 0 (y < 0) are allowed — pieces spawn partially off-screen.
        """
        s = shape if shape is not None else piece.shape
        for row_i, row in enumerate(s):
            for col_i, val in enumerate(row):
                if not val:
                    continue
                nx = piece.x + col_i + dx
                ny = piece.y + row_i + dy
                if nx < 0 or nx >= COLS or ny >= ROWS:
                    return False
                if ny >= 0 and self.grid[ny][nx]:
                    return False
        return True

    def place(self, piece: Piece) -> None:
        """Stamp the piece's color IDs into the grid at its current position."""
        for row_i, row in enumerate(piece.shape):
            for col_i, val in enumerate(row):
                if val:
                    self.grid[piece.y + row_i][piece.x + col_i] = val

    def full_rows(self) -> list[int]:
        """Return row indices that are completely filled, without clearing."""
        return [i for i, row in enumerate(self.grid) if all(row)]

    def clear_lines(self) -> int:
        """Remove all full rows, shift remaining rows down, return clear count."""
        full = self.full_rows()
        for i in full:
            self.grid.pop(i)
            self.grid.insert(0, [0] * COLS)
        return len(full)

    def ghost_y(self, piece: Piece) -> int:
        """Return the lowest y the piece can occupy without collision (ghost position)."""
        y = piece.y
        while self.is_valid(piece, dy=y - piece.y + 1):
            y += 1
        return y

    def apply_singleton_gravity(self) -> bool:
        """After a row clear, drop only completely isolated blocks.

        A block is a singleton if it has no orthogonally adjacent filled
        neighbours.  Singletons fall independently to the lowest open row in
        their column.  Processed bottom-up so multiple singletons in the same
        column settle in the correct stacking order.
        Returns True if anything moved.
        """
        singletons = []
        for row in range(ROWS):
            for col in range(COLS):
                if not self.grid[row][col]:
                    continue
                isolated = all(
                    not (0 <= row + dr < ROWS and 0 <= col + dc < COLS
                         and self.grid[row + dr][col + dc])
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
                )
                if isolated:
                    singletons.append((row, col))

        if not singletons:
            return False

        singletons.sort(reverse=True)   # bottom-up: highest row index first
        moved = False
        for row, col in singletons:
            color  = self.grid[row][col]
            target = row
            while target + 1 < ROWS and not self.grid[target + 1][col]:
                target += 1
            if target != row:
                self.grid[target][col] = color
                self.grid[row][col]    = 0
                moved = True
        return moved

    def apply_block_gravity(self) -> bool:
        """Move every block that has an empty cell directly below it down one row.

        Scans bottom-up so each block only falls one row per call.
        Returns True if anything moved.
        """
        moved = False
        for row in range(ROWS - 2, -1, -1):
            for col in range(COLS):
                if self.grid[row][col] and not self.grid[row + 1][col]:
                    self.grid[row + 1][col] = self.grid[row][col]
                    self.grid[row][col] = 0
                    moved = True
        return moved

    def settle_blocks(self) -> bool:
        """Apply block gravity repeatedly until the board is fully settled.

        Returns True if anything moved (i.e. floating blocks existed).
        """
        moved_any = False
        while self.apply_block_gravity():
            moved_any = True
        return moved_any

    def remove_color(self, color_id: int) -> list:
        """Remove every cell of color_id from the board.

        Returns a list of (col, row, color_id) tuples for particle spawning.
        """
        removed = []
        for row in range(ROWS):
            for col in range(COLS):
                if self.grid[row][col] == color_id:
                    removed.append((col, row, color_id))
                    self.grid[row][col] = 0
        return removed
