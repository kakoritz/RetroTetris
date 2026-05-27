# T3TR1S — Product Design Document

**Project:** T3TR1S  
**Repo:** [github.com/kakoritz/RetroTetris](https://github.com/kakoritz/RetroTetris)

---

## Overview

T3TR1S is a hand-built NES-style Tetris clone with no external assets. Every visual,
sound effect, and music note is generated procedurally at runtime. The goal was not to
reproduce a Tetris clone from a tutorial — it was to build something that *feels* right
from the inside out: the right weight, the right sound, the right feedback, the right
tension. Every design decision below was made in service of that feel.

---

## 1. Identity & Branding

The game is called **T3TR1S**. The byline reads *"by kakoritz"* — small, beneath the
title, not competing with it. The work should speak first. Credit is present but not
loud.

The visual language is NES: dark background, saturated tetromino colours, a Tron-style
board grid with 1px dark-cyan lines visible between cells. The grid alignment must be
pixel-exact. Misalignment breaks the aesthetic immediately and was a zero-tolerance fix
requirement.

---

## 2. Audio System

### 2.1 Layered music — 10 tiers

The music is not a single looping track. It is a ten-tier arrangement that builds in
density and complexity: tier 1 is sparse bass only, tier 10 is the full arrangement with
syncopated 16th-note bass and high-register shimmer. Each tier is a distinct layer added
on top of the previous. The player hears the music *grow* as the game progresses.

A **Music Preview screen** (accessible from the main menu) exists so each tier can be
auditioned in isolation. The sound design of the tiers is intentional and should be
iterable — the preview screen is the tool for that iteration.

### 2.2 Playback sequence

The in-game music follows a curated sequence, not a straight ascending progression:

> Tier 4 × 2 loops → Tier 5 × 2 → Tier 7 × 1 → Tier 8 × 1 → Tier 9 × 1 → Tier 6 × 2 → repeat

Tier 6 appearing *after* tier 9 is intentional — a deliberate step back in intensity
before the loop resets. The sequence should feel like a composed piece, not a level
counter.

### 2.3 Danger mode

When any block occupies the top 10 rows of the board, the music immediately drops to
tier 1 (the sparse bass-only track). Tier 1 was chosen for this role specifically because
it is the most minimal and tense tier in the arrangement.

When the board clears back below the threshold, the music **restarts the sequence from
the beginning** — not from where it left off. The reset is deliberate: surviving danger
earns a fresh start, not a resume.

### 2.4 Pause behaviour

Pausing must not silence the music. The track continues at 10% of its normal volume —
audible but not intrusive. This is a feel requirement: the game is suspended, not dead.

Volume must remain at 10% for the entire duration of the pause, including across loop
boundaries. When a music track ends naturally during a pause and a new one begins, the
10% reduction must be re-applied immediately.

---

## 3. Gameplay & Controls

### 3.1 Hard drop is instant and final

When the player presses Space to hard-drop a piece, the piece locks immediately and
synchronously. There is no gap between the drop event and the lock during which lateral
input can be accepted. This is a precision requirement — the piece goes where it lands,
not where the player accidentally nudges it after.

### 3.2 Space is the primary action key

Space is the most-used key in gameplay (hard drop). It should therefore be the primary
action key everywhere in the game flow:

- **Main menu:** Space starts the game
- **Game Over:** Space returns to the main menu

This unifies the control model. One key drives the main loop of play.

### 3.3 Danger zone warning line

A pulsing red horizontal line is drawn at the row-10 boundary whenever blocks are
present in the top half of the board. The line:

- Appears the moment danger mode triggers
- Disappears the moment the board clears below row 10
- Is drawn over the board background but under the live piece

The purpose is to give the player a visual explanation for why the music changed. The
line and the tension track are the same event — one audio, one visual. The player
connects the dots.

### 3.4 Danger zone double points

Rows cleared above the red line score double for the entire clear event. A floating
orange **×2** label spawns at each qualifying row's position and floats upward to
indicate the bonus.

This is an incentive mechanic, not just a penalty system. The danger zone is scary — it
should also be rewarding to play in. The ×2 visual makes that reward legible in the
moment it happens.

### 3.5 Perfect clear — WOW event

Clearing lines such that the board becomes **completely empty** triggers a special event:

- The entire board (every cell) flashes in a rapidly-cycling rainbow, not a plain white
  or gold flash — the *coloured* elements flash, not a screen overlay
- A large **"!! W O W !!"** popup appears centred on the board in rainbow text
- A score bonus is awarded on top of the normal line-clear score
- Maximum particle burst and screen shake fire regardless of how many lines were cleared

The distinction between a board flash and a screen flash is intentional. The rainbow
should feel like the board itself is celebrating, not like a camera effect happening over
it.

---

## 4. Scoring System

All scores are multiplied by `(level + 1)`.

| Event | Base points | In danger zone |
|-------|------------|----------------|
| Single | 40 | 80 |
| Double | 100 | 200 |
| Triple | 300 | 600 |
| Tetris (4 lines) | 1,200 | 2,400 |
| WOW bonus (perfect clear) | +5,000 | — |

The hierarchy is intentional: each tier of clear is meaningfully more valuable than the
last. The danger zone multiplier makes the top half of the board a risk/reward decision
rather than purely something to avoid. The WOW bonus is a capstone reward for an
extremely rare feat.

---

## 5. Game States & User Interface

### 5.1 GAME OVER animation

The GAME OVER text is rendered as pixel-art block letters falling from above. The
animation plays in two waves:

1. **GAME** falls first (top row), individual blocks dropping in random order with
   randomised delays
2. **OVER** falls second (bottom row), starting while GAME is still settling

Each individual block is an independent physics body. Letters must land with convincing
weight — gravity, bounce, and damping. Impact sounds fire when each complete letter
settles. The animation must complete fully before the player can advance. The player
chooses when to continue; the game does not rush them past their own death screen.

The animation speed must be calibrated so impact sounds land at the same moment the
letters visually hit. If sounds fire while letters are still falling, the timing is wrong.

### 5.2 Pause overlay

The pause screen is a full-screen overlay with the board still visible beneath it. The
PAUSE title is rendered in pixel-art block letters (matching the game's aesthetic).

Key mapping on pause:
- **Any key** resumes the game
- **Q** exits to the main menu

Q is the deliberate exit key. Escape is too easy to press accidentally mid-game. Exiting
to menu should require a conscious choice. The overlay must display this distinction
clearly.

### 5.3 Leaderboard & initials entry

The top 10 high scores are persisted to disk. On a qualifying score, the player enters
their initials before seeing the leaderboard. The game does not skip or auto-advance
this screen.

---

## 6. Settings

All settings are persisted across sessions. The settings screen is navigated with
arrow keys.

| Setting | Range | Default | Behaviour |
|---------|-------|---------|-----------|
| Music Volume | 0–100% | 40% | Applies to both menu and game music |
| SFX Volume | 0–100% | 100% | Previews immediately on adjust |
| Display Scale | 1× / 1.5× / 2× / 2.5× | 1.5× | Resizes the window; compensates for small monitors |
| Ghost Opacity | 0–100% | 15% | 0% disables the shadow entirely; 100% renders it as a solid tile |

### 6.1 Display scale

The game is designed at 460×600 logical resolution. On high-DPI or large monitors this
can appear small. The scale setting multiplies the window size while keeping the logical
resolution fixed. The game must look and play identically at every scale — only the
window size changes.

### 6.2 Ghost piece opacity

The shadow tile showing where the active piece will land should be adjustable. At 0% it
is invisible (for players who find it distracting). At 100% it looks identical to a
placed block. The default of 15% is intentionally subtle — present but not competing
with the live piece.

---

## 7. Code & Distribution Standards

### 7.1 Code quality

Code must be clean, readable, and commented where the *why* is non-obvious. No lazy
shortcuts. No dirty workarounds left in place. If something is broken, fix the root
cause. Security and correctness take priority.

### 7.2 Zero external assets

No image files. No audio files. No bundled fonts beyond what the system provides.
Everything the game needs is generated at runtime. This is a hard requirement — the
game should run from a fresh clone with only `pip install -r requirements.txt`.

### 7.3 Public distribution

The repository must be in a state where anyone can clone it and run it immediately.
The README is a first-class deliverable — not installation instructions. It must
communicate the engineering depth of the project, the full feature set, all controls
and settings, and the scoring system. It should read like a portfolio piece, not a
hobby project README.
