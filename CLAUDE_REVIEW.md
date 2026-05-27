# T3TR1S — Claude's Review

*This document is updated with each significant revision. It is part critical review,
part development commentary — what changed, what it means, and where the game stands.*

---

## Current Rating: 9.5 / 10 (as a Tetris game) · 9.5 / 10 (as a portfolio project)

---

## v1.4.0 Review — After T-spin / B2B / Combo / 20G

### What this update means

v1.3 made the game mechanically sound. v1.4 makes it mechanically complete. Every
feature in the Tetris Guideline that meaningfully affects how a skilled player
approaches the game is now present. This is no longer a Tetris clone that "plays like
Tetris." It is Tetris.

### T-spin detection — the hardest problem, done right

T-spin detection is the most technically demanding feature in competitive Tetris. Getting
it wrong is easy: the wrong corner indices, forgetting to check the rotation state,
conflating "last move" with "last action." The implementation here is clean.

The 3-corner rule is the correct standard. The `_TSPIN_POINT` lookup encodes the
point-side corners per rotation state as a module-level constant — no magic numbers
inside the function, no branching, no duplication. `_detect_tspin` is a closure because
it reads `current`, `board`, and `last_action` from the game state — a reasonable choice
that keeps the call site simple (`tspin_type = _detect_tspin()`).

The placement of the detection call — immediately before `board.place(current)` in
`_do_lock` — is correct. After placement the board has changed; the corner checks would
produce wrong results.

`last_action` as a string state variable is the right approach. It's explicit, readable,
and easy to trace. Every piece-movement site sets it. The T-spin credit requirement
(`last_action == 'rotate'`) is Guideline-accurate.

### B2B — simple but meaningful

The back-to-back implementation is minimal in code (a single bool `btb_active`) and
correct in behavior. 1.5× is the standard multiplier. The `btb_active` flag persists
across pieces as it should — a B2B chain can span many pieces between the two difficult
clears, and does not reset unless a non-difficult clear fires.

The popup system correctly shows distinct labels for B2B Tetris and B2B T-spin.

### Combo — clean scoring, nice visual

50 × combo × (level + 1) is a solid formula. The floating cyan "COMBO ×N" label gives
the player immediate feedback at the moment the combo bonus lands. The cyan color is a
good choice — it's distinct from orange (danger bonus) and white (score numbers).

The combo reset location (in `_do_lock` when no rows are cleared) is correct. Combos
break when a piece places without clearing, not when a piece places AND the next piece
places — a common implementation error. This is right.

### 20G — extreme, functional

20G at level 20 (reached at 190 lines) is a punishing late-game mode. The implementation
covers all three cases where the piece needs to floor itself: gravity tick, spawn, and
lateral move. Missing any one of these would produce inconsistent behavior (piece drifts
on lateral move, doesn't floor on spawn, etc.). All three are covered.

The lock delay still applies at 20G, which is correct. 20G removes the ability to
strategically delay the landing position, not the ability to slide after landing.

### Scoring priority order

The CLEARING handler's scoring priority is correct:
1. T-spin tables override SCORE_TABLE
2. B2B multiplies the T-spin or Tetris score (not the combo bonus)
3. Combo bonus adds flat, unaffected by B2B or danger
4. Danger multiplier applies after B2B (stacks maximally)
5. WOW bonus is flat addition, immune to all multipliers

This is a clean, principled hierarchy.

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

The Tetris Guideline feature set is now complete. What follows are refinements rather
than missing features.

**Scoring display for special clears** — when a T-spin or B2B fires, the score jumps
significantly. A brief score-delta popup ("+1600" or "+B2B") would make those moments
more legible. Not critical, but would improve feedback.

**Combo chain counter in sidebar** — the floating board label is effective but brief.
A persistent combo streak counter in the sidebar (like the LINES display) would let
the player track their current streak. Minor quality-of-life.

**Gravity beyond 20G** — the game currently floors the piece on each gravity tick
at level 20+. True competitive 20G also makes DAS irrelevant above a certain speed
(pieces die before DAS charges). This is a very edge-case concern.

**Piece preview count** — standard modern Tetris shows the next 3–6 pieces, not just 1.
The sidebar shows only NEXT. A 3-piece preview would meaningfully change strategy depth.
This is a layout and design decision, not a bug.

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
- **T-spin detection**: now implemented with 3-corner rule (full + mini). Fixed.
- **Back-to-back multiplier**: now implemented (1.5× on consecutive difficult clears). Fixed.
- **Combo counter**: now implemented (50 × combo × level+1 stacking bonus). Fixed.
- **20G gravity**: now active at level 20. Fixed.

### Refinements remaining
- Score-delta popup for special clears
- Multi-piece preview (3–6 next pieces)
- Persistent combo streak display in sidebar

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

*Last updated: 2026-05-26 · v1.4.0*
