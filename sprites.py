"""
Procedurally generated NES-style block sprites — no image files needed.
All surfaces are cached on first use so they're only built once.
"""
import pygame
from constants import COLORS, CELL_SIZE

_blocks: dict[int, pygame.Surface] = {}
_ghosts: dict[int, pygame.Surface] = {}


def _build_block(color: tuple, size: int) -> pygame.Surface:
    surf = pygame.Surface((size, size))

    hi  = tuple(min(c + 90, 255) for c in color)   # bright highlight
    hi2 = tuple(min(c + 40, 255) for c in color)   # mid highlight
    sh  = tuple(max(c - 80, 0)   for c in color)   # shadow
    border = (8, 8, 20)

    # main fill
    surf.fill(color)

    # 1-px dark outer border
    pygame.draw.rect(surf, border, (0, 0, size, size), 1)

    # inner bevel  ─ top + left = highlight, bottom + right = shadow
    pygame.draw.line(surf, hi,  (1, 1),        (size - 2, 1))
    pygame.draw.line(surf, hi,  (1, 1),        (1, size - 2))
    pygame.draw.line(surf, sh,  (2, size - 2), (size - 2, size - 2))
    pygame.draw.line(surf, sh,  (size - 2, 2), (size - 2, size - 2))

    # small highlight square in top-left corner (NES pixel detail)
    sq = max(size // 7, 2)
    pygame.draw.rect(surf, hi,  (3, 3, sq + 2, sq + 2))
    pygame.draw.rect(surf, hi2, (3, 3, sq,     sq))

    return surf


def _build_ghost(color: tuple, size: int) -> pygame.Surface:
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    ghost_fill    = (*color, 13)   # faint fill (+25 % from 10)
    ghost_outline = (*color, 56)   # dim outline (+25 % from 45)
    pygame.draw.rect(surf, ghost_fill,    (0, 0, size, size))
    pygame.draw.rect(surf, ghost_outline, (0, 0, size, size), 1)
    return surf


def get_block(color_id: int, size: int = CELL_SIZE) -> pygame.Surface:
    key = (color_id, size)
    if key not in _blocks:
        _blocks[key] = _build_block(COLORS[color_id], size)
    return _blocks[key]


def get_ghost(color_id: int, size: int = CELL_SIZE) -> pygame.Surface:
    key = (color_id, size)
    if key not in _ghosts:
        _ghosts[key] = _build_ghost(COLORS[color_id], size)
    return _ghosts[key]
