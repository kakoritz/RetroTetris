import random
import pygame
from constants import CELL_SIZE, COLORS


def spawn(clear_cells: list, quad: bool = False) -> list:
    """Return new particles bursting from the cleared row cells."""
    out   = []
    count = 3 if quad else 2
    for col, row, color_id in clear_cells:
        color = COLORS[color_id]
        for _ in range(count):
            out.append([
                float(col * CELL_SIZE + random.uniform(0, CELL_SIZE)),
                float(row * CELL_SIZE + random.uniform(0, CELL_SIZE)),
                random.uniform(-200, 200),    # vx  px/s
                random.uniform(-320, -70),    # vy  px/s  (upward)
                color,
                random.uniform(0.75, 1.0),   # life  (1 → 0)
                random.randint(2, 5),         # size  px
            ])
    return out


def update(particles: list, dt: int) -> list:
    s = dt / 1000.0
    alive = []
    for p in particles:
        p[0] += p[2] * s
        p[1] += p[3] * s
        p[3] += 420 * s      # gravity
        p[5] -= s * 1.6      # fade over ~0.6 s
        if p[5] > 0:
            alive.append(p)
    return alive


def draw(surf: pygame.Surface, particles: list) -> None:
    for p in particles:
        if p[5] <= 0:
            continue
        c = tuple(int(ch * p[5]) for ch in p[4])
        if max(c) > 0:
            pygame.draw.rect(surf, c, (int(p[0]), int(p[1]), p[6], p[6]))
