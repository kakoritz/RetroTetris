"""
touch_controls.py — virtual gamepad for Android.

6 buttons in the touch zone below the game board (y >= M_BOARD_Y + M_BOARD_H).
Pause is handled separately via M_PAUSE_RECT in the stats strip.
Call init() once from main() after the display is set up.

Layout (left → right):
  ◀  move left     (K_LEFT,  DAS-repeatable)
  ↓  soft drop     (K_DOWN,  repeatable)
  ↵  hard drop     (K_SPACE, single-fire)
  ⏹  hold piece    (K_c,     single-fire)
  ↻  rotate CW     (K_UP,    single-fire)
  ▶  move right    (K_RIGHT, DAS-repeatable)
"""
import pygame

_KEYS = [
    pygame.K_LEFT,    # < move left      (DAS-repeatable)
    pygame.K_DOWN,    # V soft drop      (repeatable)
    pygame.K_SPACE,   # ↵ hard drop      (single-fire)
    pygame.K_c,       # SWAP hold piece  (single-fire)
    pygame.K_UP,      # ↻ rotate CW      (single-fire)
    pygame.K_RIGHT,   # > move right     (DAS-repeatable)
    # Pause lives in the stats strip tap target (renderer_mobile.M_PAUSE_RECT)
]

# (Rect, key) — populated by init(); rects are in logical canvas coordinates
BUTTONS: list[tuple] = []

# Active presses: finger_id → button index
_held: dict[int, int] = {}


def init(canvas_w: int, zone_y: int, zone_h: int) -> None:
    """Set up button rects in logical canvas coordinates."""
    global BUTTONS
    n     = len(_KEYS)
    btn_w = canvas_w // n
    BUTTONS = [
        (pygame.Rect(btn_w * i,
                     zone_y,
                     btn_w if i < n - 1 else canvas_w - btn_w * (n - 1),
                     zone_h),
         _KEYS[i])
        for i in range(n)
    ]


def _hit(lx: int, ly: int) -> int | None:
    for i, (rect, _) in enumerate(BUTTONS):
        if rect.collidepoint(lx, ly):
            return i
    return None


def _post_key(evt_type: int, key: int) -> None:
    pygame.event.post(
        pygame.event.Event(evt_type, key=key, mod=0, unicode='', scancode=0)
    )


def handle(event, dw: int, dh: int,
           ox: int, oy: int, scale: float) -> None:
    """Route one FINGER* event to synthetic keyboard events."""
    if not BUTTONS:
        return

    if event.type == pygame.FINGERDOWN:
        lx = int((event.x * dw - ox) / scale)
        ly = int((event.y * dh - oy) / scale)
        idx = _hit(lx, ly)
        if idx is not None:
            _held[event.finger_id] = idx
            _post_key(pygame.KEYDOWN, BUTTONS[idx][1])

    elif event.type == pygame.FINGERUP:
        idx = _held.pop(event.finger_id, None)
        if idx is not None:
            _post_key(pygame.KEYUP, BUTTONS[idx][1])

    elif event.type == pygame.FINGERMOTION:
        if event.finger_id not in _held:
            return
        prev = _held[event.finger_id]
        lx = int((event.x * dw - ox) / scale)
        ly = int((event.y * dh - oy) / scale)
        if not BUTTONS[prev][0].collidepoint(lx, ly):
            _post_key(pygame.KEYUP, BUTTONS[prev][1])
            del _held[event.finger_id]
            idx = _hit(lx, ly)
            if idx is not None:
                _held[event.finger_id] = idx
                _post_key(pygame.KEYDOWN, BUTTONS[idx][1])
