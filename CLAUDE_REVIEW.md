# T3TR1S — Claude's Review

*This document is updated with each significant revision. It is part critical review,
part development commentary — what changed, what it means, and where the game stands.*

---

## Current Rating: 9.0 / 10 (as a Tetris game) · 9.5 / 10 (as a portfolio project)

---

## v1.3.0 Review — After Guideline Mechanics Update

### What this update meant

v1.2 was already impressive as a piece of engineering. The gap was mechanical — the
game *felt* right in places but had the kind of rough edges that a Tetris player notices
within their first five minutes: pieces getting stuck in floor rotations, the I-piece
refusing to spin near walls, no hold, no drought protection.

v1.3 closes all of those gaps. This is now a game that a competitive Tetris player can
sit down with and not feel cheated.

### 7-bag — why it matters more than it sounds

The randomiser is the most invisible fix in this update and arguably the most important.
Pure random isn't just unfair — it's *undesignable*. The scoring system, the danger zone,
the danger bonus, the WOW event: all of these are built on the assumption that the player
has a roughly fair distribution of pieces to work with. A six-Z drought isn't a skill
challenge; it's a coin flip that nullifies everything else in the design.

The 7-bag guarantee means the system works as designed. Every clever mechanic in this
game now has a fair surface to land on.

### SRS wall kicks — the silent upgrade

Most players will never consciously notice that the rotation system changed. That is
exactly right. They will notice that the game stopped silently refusing rotations they
expected to work. The I-piece spinning flush against a wall, the T-piece spinning into
a gap at the floor — these now work. The 5-test SRS tables are the standard for a reason,
and having them here means the game stops punishing players for being technically correct.

The vertical kick (`dy` offset) deserves specific mention: the old system only tried
horizontal offsets. Any rotation that needed the piece to move up slightly to clear an
overhang — a common I-piece scenario — would fail silently. That bug is gone.

### Lock delay — the feature that changes everything at high level

At low levels you will barely notice lock delay. At high levels, where the piece is
moving fast and you're stacking at the edges, it is the difference between a game that
feels responsive and one that feels like it's punishing precise play.

500 ms with a 15-reset cap is standard. The cap is important — without it, a sufficiently
patient player could hold a piece on the stack indefinitely by tapping every 499 ms.
The cap keeps the mechanic honest. Hard drop still locks instantly, which is correct:
the intent of a hard drop is finality.

### Hold piece — closing the last feature gap

Hold is the last major Tetris Guideline mechanic this game was missing. Its implementation
here is clean: reset to spawn orientation on stash, locked for the active piece's life,
visual feedback in the sidebar (dimmed when unavailable). The dimming is a good UX
decision — it communicates the locked state without text.

### Architectural note

`_start_new_game()` is a welcome consolidation. Before this change, new-game reset
logic was scattered across four call sites with slightly different sets of variables
being reset. One site was resetting popup state, another wasn't. The helper makes it
impossible for a new path into the game to forget to reset hold or lock state. This is
the kind of refactor that prevents bugs that haven't been written yet.

---

## What remains

**T-spins** are the one Guideline mechanic still absent. T-spin detection requires
tracking the last action (rotation vs. move) and checking corner occupancy — about 30
lines of code. The scoring impact is significant in competitive play (T-spin triple = 1200
base, same as a Tetris, but achievable in tight spots). This is the next natural feature.

**Back-to-back bonus** — consecutive Tetrises or T-spins in Guideline Tetris earn a 1.5×
multiplier. Not present here. Would pair naturally with T-spin detection.

**Combo counter** — consecutive clears without placing a non-clearing piece. Adds a
risk/reward dimension to chain clearing. Currently absent.

**Gravity beyond level 20** — `fall_speed` bottoms out at 80 ms/row. The game does not
implement 20G (instant gravity) for endgame levels. Not a flaw for a casual game, but
worth noting for completeness.

---

## Standing assessment across all versions

### Exceptional
- **Audio engineering**: PCM synthesis, 10-tier adaptive arrangement, real-time board
  state monitoring, pause volume management across loop boundaries. This is not something
  most indie developers ever build. It is the technical centrepiece of the project.
- **Zero-asset constraint**: every visual, sound, and note generated at runtime. Forces
  engineering depth and makes the game genuinely portable.
- **Danger zone design**: penalty + reward in the same mechanic. The red line, the music
  drop, and the 2× bonus are all expressions of the same event. Cohesive and purposeful.
- **WOW event**: proportionate to the rarity of the feat. The board itself celebrates,
  not just an overlay. The design decision (flash the cells, not the screen) was correct.

### Good
- **Feel**: DAS, screen shake, particles, per-piece spawn tones, hard-drop flash. The
  tactile feedback layer is thorough.
- **Pause behaviour**: music at 10 % rather than silent is an uncommon but right choice.
  The game is suspended, not dead. The volume-hold-across-loop-boundary fix was a real
  bug and the right fix.
- **GAME OVER animation**: per-block physics is over-engineered in the best way.

### Acceptable (was weak, now fixed)
- **Randomiser**: was pure random (drought risk), now 7-bag. Fixed.
- **Wall kicks**: were minimal (dx only, 3 tests), now full SRS (dx+dy, 5 tests per
  direction, I-piece table). Fixed.
- **Lock delay**: was absent (instant lock on grounding), now 500 ms with reset cap. Fixed.
- **Hold piece**: was absent, now implemented. Fixed.

### Still missing (not dealbreakers, but ceiling-limiters)
- T-spin detection and bonus
- Back-to-back multiplier
- Combo counter
- 20G gravity

### Architectural quality
The codebase is clean. State machine with explicit string constants, no implicit
transitions. Rendering separated from logic. Helpers for every repeated operation.
The procedural audio is well-isolated. The config persistence is minimal and correct.
The ghost tile cache (keyed by color × size × opacity) is a nice detail — lazy-built,
never rebuilt per-frame, bounded memory footprint.

The main.py is large (1200+ lines) but it is large in the right way: all the complexity
is explicit, not hidden behind abstractions that would need to be unwound to understand.
For a game of this scope and a solo author, that's the right call.

The QA instinct behind this project is real. The pause volume leak, the Esc-exits-game
bug, the sound/visual desync in GAME OVER, the text-visibility problem — these were all
caught by someone paying attention to the experience, not just the feature checklist.
That instinct is what separates a finished game from a demo.

---

*Last updated: 2026-05-26 · v1.3.0*
