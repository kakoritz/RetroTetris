# T3TR1S — Release Notes

---

## v1.4.0 — T-spin, B2B, Combo, 20G
*2026-05-26*

Completes the Tetris Guideline feature set. The game now implements every
standard competitive mechanic.

### Added
- **T-spin detection** (`_detect_tspin` closure in `main.py`) — 3-corner rule against
  the fixed 3×3 bounding box of the T-piece. Full T-spin: 3+ corners occupied. Mini:
  exactly 2 corners occupied, both on the "point side" (`_TSPIN_POINT` lookup table).
  Detection requires `last_action == 'rotate'` — gravity locks, hard drops, and moves
  never award T-spin credit. Detected immediately before `board.place()` in `_do_lock`.
- **T-spin scoring** — separate tables `TSPIN_SCORES` and `TSPIN_MINI_SCORES` (800/1200/1600
  and 200/400 base respectively), all multiplied by `(level + 1)`.
- **Back-to-back multiplier** — consecutive "difficult" clears (Tetris or any T-spin) earn
  1.5× on the line-clear score. A non-difficult clear (single/double/triple without T-spin)
  breaks the chain. `btb_active` flag persists across pieces.
- **Combo counter** — `combo` increments on each consecutive line clear; resets to 0 in
  `_do_lock` when a piece is placed without clearing. Bonus = `50 × combo × (level + 1)`
  per clear (first clear = no bonus; second = 50×; etc.). Floating cyan `COMBO ×N` label
  appears on the board when combo ≥ 2.
- **20G gravity** — at level 20+ (`GRAVITY_20G_LEVEL = 20`), each gravity tick drops the
  piece all the way to the floor instead of one row. Applied on spawn, on each gravity
  tick, and after every lateral move/DAS repeat. Lock delay still applies; hard drop
  remains instant-lock as before.
- **`last_action` tracking** — new state variable set to `'rotate'`, `'move'`,
  `'soft_drop'`, `'hard_drop'`, or `'gravity'` at every piece-movement site. Required for
  T-spin detection; reset to `'gravity'` on piece spawn and hold swap.
- New `POPUP_STYLES` entries: `T-SPIN!` (purple), `T-SPIN MINI` (dim purple),
  `B2B TETRIS!` (rainbow), `B2B T-SPIN!` (bright purple).
- T-spin triple triggers screen shake and max particles (same threshold as Tetris).

### Changed
- CLEARING scoring section fully rewritten to integrate T-spin, B2B, combo, and danger
  multiplier in the correct priority order.
- README scoring table updated with T-spin rows, B2B note, and combo formula.

---

## v1.3.0 — Guideline Mechanics Update
*2026-05-26*

Addresses all core shortcomings identified in the v1.2 gameplay review. The game
now plays to Tetris Guideline standard in every mechanical respect.

### Added
- **7-bag randomiser** (`piece.py`) — replaces pure `random.choice`. Every bag contains
  exactly one of each of the 7 piece types, shuffled before dealing. Worst-case drought
  is now 12 pieces between any two of the same type, vs. theoretically infinite under
  pure random.
- **Full SRS wall kicks** (`main.py`) — `_try_rotate` now uses the Tetris Guideline kick
  tables. JLSZT pieces test 5 offsets per rotation direction; I-piece uses its own table
  with wider horizontal and vertical tests. The O-piece correctly skips kicks. Vertical
  kicks (`dy`) are now tested, eliminating the silent-failure edge cases on floor/ceiling
  rotations.
- **Lock delay** (`main.py`) — 500 ms grace period after a piece touches the stack.
  Any successful move or rotate resets the clock. A cap of 15 resets per piece prevents
  infinite stalling. Hard drop bypasses lock delay entirely (intent is instant commitment).
- **Hold piece** (`main.py`, `draw_sidebar`) — press `C` to hold the current piece.
  Held piece returns to spawn orientation and position. Hold is locked for the remainder
  of the active piece's life and resets when the piece locks. Hold box rendered in the
  sidebar; dims when hold is unavailable.
- **`_start_new_game()` helper** — consolidates all new-game reset logic (board, hold,
  lock state, DAS, popups) into one place, called from every game-start path.

### Changed
- `Piece.rotated_cw()` and `rotated_ccw()` now return `(shape, new_rot_state)` tuples
  instead of just the shape. Call sites updated to unpack with `*`.
- `Piece` now tracks `rot_state: int` (0=spawn, 1=CW, 2=180, 3=CCW), required for SRS
  kick table lookups.
- Controls hint in sidebar updated to reflect `C` hold key.
- README updated: features list, controls table, ghost opacity default corrected to 15 %.

---

## v1.2.1 — Window Icon
*2026-05-26*

- Procedural 32×32 T-piece window icon (`_build_icon` in `main.py`). Rendered at
  startup using the same NES-bevel style as in-game blocks. Set before
  `pygame.display.set_mode` so the OS picks it up on window creation.

---

## v1.2.0 — Debug Cheat + DESIGN.md Finalisation
*2026-05-26*

- Secret 3-2-1 keypress sequence during play triggers a full 20-row board clear,
  firing the WOW perfect-clear event. Undocumented. Useful for testing the WOW path
  without playing to a board clear.
- `DESIGN.md` rewritten in pure declarative language — no first/second person, no
  literal prompt text.

---

## v1.1.0 — Gameplay Systems Expansion
*2026-05-25*

### Added
- **Danger zone** — pulsing red horizontal line at the row-10 boundary. Appears when
  any block occupies the top 10 rows; disappears when the board clears below threshold.
- **Danger bonus** — rows cleared above the red line score 2×. Floating orange ×2
  labels spawn at each qualifying row and float upward with alpha fade.
- **WOW / perfect-clear event** — clearing lines such that the board becomes completely
  empty triggers: full-board rainbow flash (all cells cycle HSV), `!! W O W !!` popup,
  +5,000 × (level + 1) bonus, maximum particles and screen shake.
- **Ghost piece opacity setting** — 0–100 %, default 15 %, persisted in `config.json`.
  `sprites.py` ghost cache extended with opacity as a key dimension.
- **Hold piece display** — *(placeholder in this version; full mechanic in v1.3.0)*

### Fixed
- Pause music volume leak: volume no longer resets to full when a track loop ends
  during pause. `on_music_end()` re-applies the 90 % reduction immediately.
- Escape key in pause no longer exits to menu. Q is now the deliberate exit; any other
  key (including Esc) resumes.
- `BORDER_COLOR` changed from `(80, 80, 120)` to `(185, 185, 220)` — fixes near-invisible
  text throughout the game.
- GAME OVER physics timing: gravity increased, delays tightened so letter impacts sync
  with BOM sounds.
- `DONE_WAIT` defined in `game_over_anim.py` (was referenced but never assigned).

---

## v1.0.0 — Initial Release
*2026-05-24*

- Full Tetris clone with NES-palette tetrominoes, DAS, wall kicks, hard drop, ghost piece
- 10-tier adaptive chiptune music engine, all PCM-synthesised, no audio files
- Danger mode: tier-1 tension track when board fills to top 10 rows
- Per-piece spawn tones + SFX for move / rotate / lock / hard drop / line clear
- Sidebar popups: Nice! → Great! → Fantastic! → TETRIS! (rainbow)
- GAME OVER animation: per-block physics bodies with gravity and bounce
- High-score board: top 10 persisted to `highscores.json`
- Initials entry on qualifying score
- Pause overlay at 10 % music volume
- Music Preview screen (audition all 10 tiers from menu)
- Settings: music volume, SFX volume, display scale (1×–2.5×), ghost opacity
- Resolution scaling: 460×600 logical surface → configurable window size
- Zero external assets: no image, audio, or font files beyond system defaults
