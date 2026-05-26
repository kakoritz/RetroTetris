import random
from constants import SHAPES, COLS


class Piece:
    def __init__(self):
        self.type = random.choice(list(SHAPES.keys()))
        self.shape = [row[:] for row in SHAPES[self.type]]
        self.x = COLS // 2 - len(self.shape[0]) // 2
        self.y = 0

    def rotated_cw(self) -> list[list[int]]:
        return [list(row) for row in zip(*self.shape[::-1])]

    def rotated_ccw(self) -> list[list[int]]:
        return [list(row) for row in zip(*self.shape)][::-1]

    @property
    def color_id(self) -> int:
        for row in self.shape:
            for v in row:
                if v:
                    return v
        return 0

    # backward-compat alias
    def rotated(self) -> list[list[int]]:
        return self.rotated_cw()
