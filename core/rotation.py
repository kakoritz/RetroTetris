# rotation.py — SRS rotation and T-spin detection, extracted from main.py
import audio
from board import Board
from piece import Piece
from constants import COLS, ROWS
from game_constants import _KICKS_JLSZT, _KICKS_I, _TSPIN_POINT


def try_rotate(board: Board, piece: Piece,
               new_shape: list, new_state: int) -> bool:
    """Attempt rotation with full SRS wall kicks.

    Tries each kick offset for the given state transition in order.
    On the first valid position the piece is updated and True is returned.
    """
    key   = (piece.rot_state, new_state)
    table = _KICKS_I if piece.type == 'I' else _KICKS_JLSZT
    kicks = table.get(key, [(0, 0)]) if piece.type != 'O' else [(0, 0)]

    for dx, dy in kicks:
        if board.is_valid(piece, dx=dx, dy=dy, shape=new_shape):
            piece.x        += dx
            piece.y        += dy
            piece.shape     = new_shape
            piece.rot_state = new_state
            audio.play('rotate')
            return True
    return False


def detect_tspin(board: Board, piece: Piece, last_action: str) -> str | None:
    """Return 'full', 'mini', or None based on T-spin corner rule.

    Full T-spin: last action was a rotation, piece is T, and 3+ of the 4
    corners of the 3×3 bounding box are occupied (wall or stack).
    Mini: exactly 2 corners occupied and both are on the point side.
    """
    if piece.type != 'T' or last_action != 'rotate':
        return None
    px, py = piece.x, piece.y
    corners = [(px, py), (px+2, py), (px, py+2), (px+2, py+2)]

    def _blocked(cx: int, cy: int) -> bool:
        return (cx < 0 or cx >= COLS or cy >= ROWS
                or (cy >= 0 and board.grid[cy][cx] != 0))

    flags = [_blocked(cx, cy) for cx, cy in corners]
    n     = sum(flags)

    if n >= 3:
        return 'full'
    if n == 2:
        pi, pj = _TSPIN_POINT[piece.rot_state]
        if flags[pi] and flags[pj]:
            return 'mini'
    return None
