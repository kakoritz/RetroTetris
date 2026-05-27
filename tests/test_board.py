"""Unit tests for board.py — grid logic, collision, line clearing, cascade gravity."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from board import Board
from piece import Piece
from constants import COLS, ROWS, SHAPES


def make_piece(piece_type: str) -> Piece:
    """Create a Piece of a specific type regardless of bag state."""
    p = Piece.__new__(Piece)
    p.type      = piece_type
    p.shape     = [row[:] for row in SHAPES[piece_type]]
    p.x         = COLS // 2 - len(p.shape[0]) // 2
    p.y         = 0
    p.rot_state = 0
    return p


# ── helpers ───────────────────────────────────────────────────────────────────

def make_board(*row_strs):
    """Build a Board from a list of row strings (bottom = last element).

    Each char: '.' = empty, any digit = that color_id.
    Rows not supplied default to empty; rows are bottom-aligned.
    """
    b = Board()
    for i, s in enumerate(row_strs):
        row_idx = ROWS - len(row_strs) + i
        for col, ch in enumerate(s):
            b.grid[row_idx][col] = int(ch) if ch != '.' else 0
    return b


def full_row(color_id=1):
    return str(color_id) * COLS


def empty_row():
    return '.' * COLS


# ── is_valid ──────────────────────────────────────────────────────────────────

def test_is_valid_empty_board():
    b = Board()
    p = make_piece('I')
    p.x, p.y = 0, 0
    assert b.is_valid(p)


def test_is_valid_out_of_bounds_left():
    b = Board()
    p = make_piece('I')
    p.x, p.y = -1, 5
    assert not b.is_valid(p)


def test_is_valid_out_of_bounds_right():
    b = Board()
    p = make_piece('I')
    p.x, p.y = COLS - 2, 5   # I-piece is 4 wide, so col COLS-2+3 = COLS+1 > COLS
    assert not b.is_valid(p)


def test_is_valid_collision():
    b = make_board(full_row(1))
    p = make_piece('O')
    p.x, p.y = 0, ROWS - 2   # O is 2 tall, bottom row full → collision
    assert not b.is_valid(p)


def test_is_valid_above_stack():
    b = make_board(full_row(1))
    p = make_piece('O')
    p.x, p.y = 0, ROWS - 3   # one row above the full row — valid
    assert b.is_valid(p)


# ── full_rows ─────────────────────────────────────────────────────────────────

def test_full_rows_empty():
    b = Board()
    assert b.full_rows() == []


def test_full_rows_single():
    b = make_board(full_row(2))
    assert b.full_rows() == [ROWS - 1]


def test_full_rows_multiple():
    b = make_board(full_row(1), full_row(2))
    rows = b.full_rows()
    assert len(rows) == 2
    assert ROWS - 2 in rows
    assert ROWS - 1 in rows


def test_partial_row_not_full():
    b = make_board('1111.....1')
    assert b.full_rows() == []


# ── clear_lines ───────────────────────────────────────────────────────────────

def test_clear_lines_removes_full_rows():
    b = make_board(full_row(3))
    assert b.clear_lines() == 1
    assert b.full_rows() == []
    assert all(b.grid[ROWS - 1][c] == 0 for c in range(COLS))


def test_clear_lines_shifts_rows_down():
    b = make_board('1.........',   # partial row (survives)
                   full_row(2))    # full row (cleared)
    b.clear_lines()
    # The partial row should now be at the bottom
    assert b.grid[ROWS - 1][0] == 1
    assert b.grid[ROWS - 1][1] == 0


def test_clear_lines_double():
    b = make_board(full_row(1), full_row(2))
    assert b.clear_lines() == 2
    assert all(b.grid[r][c] == 0 for r in range(ROWS) for c in range(COLS))


# ── settle_blocks / cascade gravity ──────────────────────────────────────────

def test_settle_blocks_drops_floating():
    """A block with empty space below it should fall after settle_blocks."""
    b = Board()
    b.grid[0][0] = 1   # lone block at very top
    b.settle_blocks()
    assert b.grid[0][0] == 0
    assert b.grid[ROWS - 1][0] == 1


def test_settle_blocks_stacks_correctly():
    """Two blocks in the same column should stack, not leapfrog."""
    b = Board()
    b.grid[0][0] = 1
    b.grid[1][0] = 2
    b.settle_blocks()
    assert b.grid[ROWS - 1][0] == 2
    assert b.grid[ROWS - 2][0] == 1


def test_settle_blocks_resting_unchanged():
    b = make_board(full_row(1))
    moved = b.settle_blocks()
    assert not moved   # nothing to fall


# ── remove_color ──────────────────────────────────────────────────────────────

def test_remove_color_clears_all():
    b = make_board('1111......', '22........')
    removed = b.remove_color(1)
    assert len(removed) == 4
    assert all(b.grid[r][c] != 1 for r in range(ROWS) for c in range(COLS))


def test_remove_color_leaves_others():
    b = make_board('1234567123')
    b.remove_color(1)
    # Color 2-7 should still exist
    row = b.grid[ROWS - 1]
    assert 2 in row
    assert 1 not in row


def test_remove_color_returns_positions():
    b = Board()
    b.grid[5][3] = 4
    b.grid[10][7] = 4
    removed = b.remove_color(4)
    positions = {(col, row) for col, row, _ in removed}
    assert (3, 5) in positions
    assert (7, 10) in positions


def test_remove_color_empty_board_returns_empty():
    b = Board()
    assert b.remove_color(3) == []


# ── mono-color row detection (color clear trigger) ───────────────────────────

def test_mono_color_row_detected():
    """A row where all 10 cells share the same color_id is a color-clear row."""
    b = make_board(full_row(3))   # all cells color 3
    row = b.grid[ROWS - 1]
    colors = set(row)
    assert len(colors) == 1 and next(iter(colors)) == 3


def test_mixed_color_row_not_mono():
    b = make_board('1234567123')
    row = b.grid[ROWS - 1]
    assert len(set(row)) > 1


# ── place ────────────────────────────────────────────────────────────────────

def test_place_writes_color_id():
    b = Board()
    p = make_piece('O')
    p.x, p.y = 0, ROWS - 2
    b.place(p)
    assert b.grid[ROWS - 2][0] == p.color_id
    assert b.grid[ROWS - 1][0] == p.color_id


def test_place_does_not_overwrite_others():
    b = Board()
    b.grid[ROWS - 1][5] = 7   # pre-existing block
    p = make_piece('I')
    p.x, p.y = 0, ROWS - 1
    b.place(p)
    assert b.grid[ROWS - 1][5] == 7   # untouched (I placed at cols 0-3)
