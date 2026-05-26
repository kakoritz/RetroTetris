from constants import COLS, ROWS
from piece import Piece


class Board:
    def __init__(self):
        self.grid: list[list[int]] = [[0] * COLS for _ in range(ROWS)]

    def is_valid(self, piece: Piece, dx: int = 0, dy: int = 0,
                 shape: list[list[int]] | None = None) -> bool:
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
        for row_i, row in enumerate(piece.shape):
            for col_i, val in enumerate(row):
                if val:
                    self.grid[piece.y + row_i][piece.x + col_i] = val

    def full_rows(self) -> list[int]:
        """Return row indices that are completely filled, without clearing."""
        return [i for i, row in enumerate(self.grid) if all(row)]

    def clear_lines(self) -> int:
        full = self.full_rows()
        for i in full:
            self.grid.pop(i)
            self.grid.insert(0, [0] * COLS)
        return len(full)

    def ghost_y(self, piece: Piece) -> int:
        y = piece.y
        while self.is_valid(piece, dy=y - piece.y + 1):
            y += 1
        return y
