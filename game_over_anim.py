"""
game_over_anim.py — Pixel-art GAME OVER block-letter animation.

Layout:
  - "GAME" falls first (top row, y≈230).  Blocks scatter across a 0–900 ms
    random-delay window so they arrive in chaos order rather than all at once.
  - "OVER" falls second (bottom row, y≈320).  Delays start at 1 300 ms so
    "OVER" begins dropping while "GAME" is still settling.

Each block is an independent physics body:
  • Released after its individual delay expires.
  • Accelerates downward under GRAVITY.
  • Bounces on impact with DAMPING until vertical speed drops below MIN_VEL,
    at which point it sticks to its target position.

A BOM impact sound fires the moment every block in a letter has stuck.
After all 8 letters have landed, "PRESS ANY KEY" is shown and the game
waits for input before advancing to the high-score or game-over screen.
"""

import random
import pygame
from constants import BOARD_WIDTH, BOARD_HEIGHT, COLORS


# ── pixel font (5×5 grid, 1 = filled block) ──────────────────────────────────

_GLYPHS = {
    'G': [[0,1,1,1,0],
          [1,0,0,0,0],
          [1,0,1,1,1],
          [1,0,0,0,1],
          [0,1,1,1,0]],
    'A': [[0,1,1,0,0],
          [1,0,0,1,0],
          [1,1,1,1,0],
          [1,0,0,1,0],
          [1,0,0,1,0]],
    'M': [[1,0,0,0,1],
          [1,1,0,1,1],
          [1,0,1,0,1],
          [1,0,0,0,1],
          [1,0,0,0,1]],
    'E': [[1,1,1,1,0],
          [1,0,0,0,0],
          [1,1,1,0,0],
          [1,0,0,0,0],
          [1,1,1,1,0]],
    'O': [[0,1,1,1,0],
          [1,0,0,0,1],
          [1,0,0,0,1],
          [1,0,0,0,1],
          [0,1,1,1,0]],
    'V': [[1,0,0,0,1],
          [1,0,0,0,1],
          [0,1,0,1,0],
          [0,1,0,1,0],
          [0,0,1,0,0]],
    'R': [[1,1,1,1,0],
          [1,0,0,0,1],
          [1,1,1,1,0],
          [1,0,1,0,0],
          [1,0,0,1,0]],
}

# ── layout constants ──────────────────────────────────────────────────────────

_BLOCK = 10    # filled square size in pixels
_CELL  = 12    # block + 2 px transparent gap (produces the grid-line look)
_LGAP  = 8     # pixels of space between adjacent letters

_LETTER_W = 5 * _CELL   # each letter is 5 columns wide = 60 px

# Letter specs: (character, bom_index).
# bom_index is passed back to the caller so it can fire the right impact sound.
_GAME_SPEC = [('G', 1), ('A', 2), ('M', 3), ('E', 4)]   # top row,    falls first
_OVER_SPEC = [('O', 5), ('V', 6), ('E', 7), ('R', 8)]   # bottom row, falls second

# Tetromino color IDs assigned per letter so the word uses varied NES colours.
_LETTER_COLOR_ID = {1: 1, 2: 7, 3: 3, 4: 6, 5: 5, 6: 4, 7: 2, 8: 1}

# ── physics ───────────────────────────────────────────────────────────────────

GRAVITY  = 5000   # px / s²  — high gravity = snappy, weighty feel
DAMPING  = 0.32   # fraction of velocity retained on each bounce (0 = no bounce)
MIN_VEL  = 160    # px / s   — below this on impact the block sticks permanently

# ── timing ────────────────────────────────────────────────────────────────────
# Total animation completes in roughly 2.5–3 s.
#
# GAME (delay 0–900 ms): all blocks start falling within the first second.
# OVER (delay 1300–2300 ms): begins dropping while GAME is still settling,
#   producing overlapping chaos rather than two discrete phases.

_GAME_DELAY_MIN   =    0   # ms — earliest a GAME block can start falling
_GAME_DELAY_RANGE =  900   # ms — spread window for GAME block start times
_OVER_DELAY_MIN   = 1300   # ms — earliest an OVER block can start falling
_OVER_DELAY_RANGE = 1000   # ms — spread window for OVER block start times

# How long after all_landed before is_finished() returns True.
# Not used by main.py (which checks all_landed directly), but kept for
# forward-compatibility if a caller wants automatic advancement.
DONE_WAIT = 2000   # ms

# ── font cache ────────────────────────────────────────────────────────────────

_FONT_CACHE: dict = {}


def _f(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = pygame.font.SysFont("monospace", size, bold=bold)
    return _FONT_CACHE[key]


# ── layout helper ─────────────────────────────────────────────────────────────

def _letter_start_x(letter_index: int) -> int:
    """Pixel x of the left edge of the letter at position letter_index (0–3)."""
    total = 4 * _LETTER_W + 3 * _LGAP
    return (BOARD_WIDTH - total) // 2 + letter_index * (_LETTER_W + _LGAP)


# ── main class ────────────────────────────────────────────────────────────────

class GameOverAnim:
    """Drives the falling-block GAME OVER animation.

    Lifecycle:
        anim = GameOverAnim()          # or call anim.reset() to reuse
        while True:
            boms = anim.update(dt_ms)  # advance physics; returns landed-letter IDs
            for b in boms:
                audio.play_bom(b)
            anim.draw(surface)
            if anim.all_landed:
                ...wait for keypress, then transition...
    """

    def __init__(self) -> None:
        # _blocks: list of per-block physics dicts (see _add_letter for keys).
        self._blocks:       list = []
        # Tracks whether every block in each letter has stuck.
        self._letter_done:  dict = {}   # bom_idx (int) → bool
        # Set to True once every single block in the animation has landed.
        self.all_landed:    bool = False
        # Darkening overlay alpha — ramps from 0 → 200 over ~1 s.
        self.overlay_alpha: int  = 0
        # Counts ms elapsed since all_landed became True.
        self._done_timer:   int  = 0
        self._build()

    # ── construction ─────────────────────────────────────────────────────────

    def _build(self) -> None:
        GAME_TOP = 230   # pixel y of the top row of "GAME" glyphs
        OVER_TOP = 320   # pixel y of the top row of "OVER" glyphs

        for li, (ch, bom) in enumerate(_GAME_SPEC):
            self._add_letter(ch, bom, _letter_start_x(li), GAME_TOP,
                             _GAME_DELAY_MIN, _GAME_DELAY_RANGE)

        for li, (ch, bom) in enumerate(_OVER_SPEC):
            self._add_letter(ch, bom, _letter_start_x(li), OVER_TOP,
                             _OVER_DELAY_MIN, _OVER_DELAY_RANGE)

    def _add_letter(self, ch: str, bom_idx: int,
                    lx: int, top_y: int,
                    delay_min: int, delay_range: int) -> None:
        """Spawn all filled pixels of glyph `ch` as independent physics blocks.

        Each block gets its own random delay (within the letter's window) and
        a random starting height slightly above the top of the screen.  This
        produces the "raining" chaos-order effect even within a single letter.
        """
        color = COLORS.get(_LETTER_COLOR_ID[bom_idx], (255, 255, 255))
        self._letter_done[bom_idx] = False

        for gy in range(5):
            for gx in range(5):
                if not _GLYPHS[ch][gy][gx]:
                    continue
                tx = lx + gx * _CELL                     # final x (never changes)
                ty = float(top_y + gy * _CELL)           # final y (landing target)
                # Start position: a small random distance above the screen top.
                # Keeping this shallow (10–120 px) ensures each block is visible
                # shortly after its delay expires, tying the visual appearance
                # closely to the audio impact timing.
                start_y = float(-_BLOCK - random.randint(10, 120))
                self._blocks.append({
                    'tx':     tx,
                    'ty':     ty,
                    'x':      float(tx),   # x is constant; kept for draw loop symmetry
                    'y':      start_y,
                    'vy':     0.0,         # vertical velocity, px / s (positive = down)
                    'delay':  random.randint(delay_min, delay_min + delay_range),
                    'color':  color,
                    'bom':    bom_idx,
                    'landed': False,
                })

    # ── public API ────────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Rebuild the animation from scratch (call before each new game over)."""
        self._blocks       = []
        self._letter_done  = {}
        self.all_landed    = False
        self.overlay_alpha = 0
        self._done_timer   = 0
        self._build()

    def update(self, dt: int) -> list:
        """Advance the animation by `dt` milliseconds.

        Returns a list of bom_idx values for letters that fully landed this
        frame.  The caller should fire an impact sound for each returned index.
        """
        s = dt / 1000.0   # seconds this frame

        # Darken the board background to make the letters stand out.
        # Reaches full opacity (~200/255) after roughly 870 ms.
        self.overlay_alpha = min(200, self.overlay_alpha + int(230 * s))

        for blk in self._blocks:
            if blk['landed']:
                continue

            # Count down the per-block release delay.
            blk['delay'] -= dt
            if blk['delay'] > 0:
                continue

            # Physics: constant downward acceleration.
            blk['vy'] += GRAVITY * s
            blk['y']  += blk['vy'] * s

            # Impact check: block has reached or passed its target row.
            if blk['y'] >= blk['ty']:
                blk['y'] = blk['ty']
                if blk['vy'] > MIN_VEL:
                    # Still moving fast enough to bounce.
                    blk['vy'] = -blk['vy'] * DAMPING
                else:
                    # Speed is low — stick permanently.
                    blk['vy']     = 0.0
                    blk['landed'] = True

        # Determine which letters completed this frame (all their blocks stuck).
        just_bom: list = []
        for bom_idx, already_done in self._letter_done.items():
            if already_done:
                continue
            letter_blocks = [b for b in self._blocks if b['bom'] == bom_idx]
            if letter_blocks and all(b['landed'] for b in letter_blocks):
                self._letter_done[bom_idx] = True
                just_bom.append(bom_idx)

        # Check global completion.
        if not self.all_landed:
            if self._blocks and all(b['landed'] for b in self._blocks):
                self.all_landed = True
        if self.all_landed:
            self._done_timer += dt

        return just_bom

    def is_finished(self) -> bool:
        """Returns True once all blocks have landed AND DONE_WAIT ms have elapsed.

        main.py checks all_landed directly and waits for a keypress instead,
        so this is provided for any caller that wants automatic advancement.
        """
        return self.all_landed and self._done_timer >= DONE_WAIT

    def draw(self, surf: pygame.Surface) -> None:
        """Render the current animation frame onto `surf`."""

        # Semi-transparent darkening overlay so letters read against the board.
        if self.overlay_alpha > 0:
            ov = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, self.overlay_alpha))
            surf.blit(ov, (0, 0))

        for blk in self._blocks:
            # Skip blocks still in their pre-fall delay window.
            if blk['delay'] > 0:
                continue
            y = int(blk['y'])
            # Skip blocks that haven't scrolled onto the screen yet.
            if y < -_BLOCK:
                continue
            x   = int(blk['x'])
            col = blk['color']

            # Main filled face.
            pygame.draw.rect(surf, col, (x, y, _BLOCK, _BLOCK))

            # Top and left highlight edge (+90 brightness) — gives the NES 3-D bevel look.
            bright = tuple(min(255, c + 90) for c in col)
            pygame.draw.line(surf, bright, (x,           y),           (x + _BLOCK - 1, y),           1)
            pygame.draw.line(surf, bright, (x,           y),           (x,              y + _BLOCK - 1), 1)

            # Bottom and right shadow edge (-60 brightness).
            dark = tuple(max(0, c - 60) for c in col)
            pygame.draw.line(surf, dark,   (x + _BLOCK - 1, y),           (x + _BLOCK - 1, y + _BLOCK - 1), 1)
            pygame.draw.line(surf, dark,   (x,              y + _BLOCK - 1), (x + _BLOCK - 1, y + _BLOCK - 1), 1)

        # Once every block has landed, prompt the player to continue.
        if self.all_landed:
            t = _f(14).render("PRESS  ANY  KEY", True, (200, 200, 200))
            surf.blit(t, (BOARD_WIDTH // 2 - t.get_width() // 2,
                          BOARD_HEIGHT - 46))
