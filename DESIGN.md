# T3TR1S — Product Design Document

**Author:** kakoritz  
**Project:** T3TR1S (RetroTetris)  
**Purpose:** This document records the product intent, design decisions, and feature
rationale behind every enhancement made to T3TR1S. Every section originates from a
deliberate design directive from the project author. This is not a generated summary
of what was built — it is a record of what was *asked for* and *why*.

---

## 1. Brand & Identity

### 1.1 Title treatment
The game title is **T3TR1S**. The subtitle "KAKORITZ'S" was explicitly removed because
it was judged to look *"cheesey"* by the author. The replacement treatment — small
*"by kakoritz"* text beneath the title — was the author's specific solution: credit
without ego. The distinction matters: the work stands on its own, the author's name is
present but secondary.

### 1.2 Visual tone
The aesthetic target is NES-era: dark background, vivid tetromino colours, a Tron-style
board grid. The board was intentionally redesigned with a **dark cyan 1px grid line**
visible between cells (`_BOARD_LINE`) and a near-black cell fill (`_BOARD_CELL`). This
was not a default — it was a correction to a misalignment bug the author noticed and
specifically called out: *"the grid lines not matching cell boundaries."*

---

## 2. Audio Philosophy

### 2.1 Layered music system (10 tiers)
The author's core requirement was that the music should **build and evolve** rather than
loop a single track. The tier system was entirely the author's concept: sparse bass at
tier 1, progressively adding arpeggios, melody, syncopation, and shimmer up to tier 10.
The author wanted to *hear and feel* each tier before committing to when they played —
hence the Music Preview screen.

### 2.2 Music sequence
The playback order was specified precisely by the author:
> *"tier 4 — 2 loops / t5 — 2 loops / t7 — 1 loop / t8 1 loop / t9 1 loop / t6 — 2 loops / repeat"*

This is not a default progression — it is a curated arrangement. Tier 6 appearing after
tier 9 (a deliberate step back in intensity before the loop repeats) reflects an
intentional narrative arc in the music.

### 2.3 Danger mode
The author defined the danger threshold independently: *"if at any point the game is
getting close to ending and the bricks are landing in the top 10 slots, drop to tier 1
music."* Tier 1 (sparse whole-note bass pulse) was chosen specifically because it is
the most tense and minimal tier. The recovery behaviour — *"once it goes back up to 11+
(or down rather) then resume the music from the start sequence"* — was also the author's
explicit call. Resuming from the top of the sequence rather than from where it left off
was a deliberate reset.

### 2.4 Music Preview screen
The author wanted to audition tiers before committing to the sequence design:
> *"I want a special menu option for MUSIC where I can hear each level's music. Select
> level 1 and 2 and so on so I can hear and feel it because I want to make some changes
> of which tones are played when."*

The preview screen (`T` from the menu) was built specifically so the author could iterate
on the sound design with ears, not assumptions.

### 2.5 Pause volume behaviour
The author specified that pausing should *drop* the music volume by 90%, not stop it.
The overlay exists; the music persists — just quieter. This was a deliberate feel
decision, not a default.

---

## 3. Gameplay Mechanics

### 3.1 Hard-drop lock (Space)
The author identified a specific bug: *"Space-dropped piece could be shifted before
locking."* The fix requirement was explicit — the piece must lock immediately and
synchronously when Space is pressed, with no window for lateral input between the drop
and the lock. This is a precision gameplay decision, not a minor bug fix.

### 3.2 Space as the primary action key
The author made a deliberate UX decision:
> *"since the main mechanic button is Space, it's used as the main action key. Therefore
> it should be the main action key in new game and game over."*

Space starts the game from the menu. Space at game over returns to menu. This unifies
the mental model — one key drives the main loop of play.

### 3.3 Danger zone warning line
The author's reasoning was empathy-driven:
> *"when the tier 1 music kicks in it might throw people off, so maybe add a red line
> that they crossed across the board so they can connect the dots."*

The line is the visual anchor for why the music changed. It appears when danger triggers
and disappears when the board clears — the connection is direct and self-explanatory.

### 3.4 Danger zone double points
The author wanted danger to carry an incentive, not just a penalty:
> *"any rows cleared above the red line should be double points and that should be
> indicated somewhere on the screen with ×2 signs floating up — as an incentive to
> play in the red."*

Two design choices in one: a mechanical reward (2× score) and a visual reward (floating
orange ×2 labels). Playing dangerously should feel *good*, not just scary.

### 3.5 Perfect clear (WOW event)
The author initiated this feature entirely:
> *"I want something awesome to happen if you somehow clear the whole board. I know we
> have TETRIS if you clear 4. But it's going to be an amazing feat to clear a board. So
> maybe !! W O W !! but then maybe the whole game flashes — like the present graphics
> that exist all flash the same way the 4-row flash does. Not a screen flash. Anything
> with colour flashes that way."*

The distinction the author drew — *not* a screen-wide white flash but specifically the
**coloured elements** flashing — is a meaningful visual design call. The rainbow cycle
over every board cell, rather than a blanket white overlay, honours that distinction.

### 3.6 Scoring system awareness
The author explicitly asked to understand the current scoring table:
> *"What kind of bonuses do we give out for clearing rows in single, double, triple, and
> Tetris clear?"*

This was not a passive question — it preceded the danger-zone 2× bonus design, showing
the author was building a coherent reward hierarchy: single → double → triple → Tetris →
danger zone multiplier → perfect clear bonus.

---

## 4. User Interface & Game States

### 4.1 GAME OVER animation — letter order
The author corrected the initial implementation:
> *"on game over — do the GAME word first and the OVER part second."*

The sequencing is intentional: GAME lands, then OVER lands on top. The reading order
of the words is preserved in the animation timeline.

### 4.2 GAME OVER — require keypress to advance
> *"make it so you have to press a button to continue to high score — it doesn't just
> rush you to high score."*

The author did not want the player to be swept past their own death screen. The animation
plays fully, all letters land, and the player chooses when to move on. Control stays
with the player.

### 4.3 GAME OVER — animation speed and sound sync
The author identified a desync between visuals and audio:
> *"your sound effects for the GAME OVER are off. The sound effects happen before the
> letters drop. Maybe make the letters fall faster to time with the sounds."*

The author's proposed fix (faster falls) was the right one. Higher gravity, tighter
delay windows, shallower starting heights — the fix was physics, and the author
diagnosed it correctly.

### 4.4 Pause menu — exit key safety
> *"the escape menu — if you press escape in the escape menu it takes you out of the
> game. That can't happen. It should be something hard like press Q to exit. Any key to
> resume."*

The author's reasoning is clear: Escape is too easy to press accidentally. Q is
deliberate. This is an intentional friction point — exiting to menu mid-game should
require a choice, not a reflex.

### 4.5 Pause menu — music volume stability
The author caught a specific bug:
> *"when the current music loop ends and the next loop kicks in during pause, the sound
> goes back to normal. So there needs to be a check if in the pause menu that all loops
> are 90%."*

This is an audio state management requirement, not a general bug report. The author
understood the mechanism (loop end triggers a new track start, which resets volume) and
specified the fix (re-apply the reduction after each new track starts).

---

## 5. Settings & Personalisation

### 5.1 Display scale
The author identified that the game appeared small on some monitors and wanted a
systematic solution:
> *"is it possible to add a graphic section to change scale? On some monitors this is
> really small."*

The author asked for a plan first, validated the approach, then approved implementation.
The four scale options (1×, 1.5×, 2×, 2.5×) and their persistence across sessions were
a direct response to a real usability concern.

### 5.2 Ghost piece opacity
The author wanted the shadow tile to be user-adjustable:
> *"I want another game setting option for shadow tile piece darkness scale or something
> so you can turn it to zero — off — or all the way to looking like a full tile, but it
> should start at like 25% default."*

Three distinct states were specified: invisible (0), default (low %), and solid
(100%). The author subsequently refined the default:
> *"I think 15% is better default for ghost overlay."*

This reflects iterative design ownership — the author had a feel target and adjusted
toward it.

---

## 6. Code Quality & Documentation Standards

### 6.1 Code quality directive
The author issued a clear quality mandate:
> *"ensure that the code is robust and clean and sexy. No laziness. Add notes and
> comments into what's going on. Check for security holes or anything that needs
> enhanced or clean. No dirty code please."*

The standard is: readable, commented where non-obvious, defensively written.

### 6.2 README as professional document
The author gave explicit intent for the README:
> *"in the README I don't want people to think I just vibe-coded this into existence and
> it's hand-wave dismissed. So in the README, engineer how this came to be and the level
> of effort on my part somehow, so it looks professional and not a half-ass project."*

And separately, as features accumulated:
> *"all these little things we are adding to the game — settings, point systems — should
> be in the README file. Assume this README file is a job interview and people want to
> know what this is."*

The README is a portfolio document, not installation instructions. It should communicate
engineering depth, design intent, and the breadth of systems built.

### 6.3 GitHub distribution
The author explicitly considered their audience:
> *"I want this cleanly uploaded to GitHub so my friends can download it."*

And later commissioned this design document specifically to show the project was driven
by intentional authorship:
> *"take a look at every one of my prompts this whole time and generate a PDD or SOP
> type document coming only from my prompts that lay out clearly what it is I want out
> of all of this — to show this wasn't just Claude-generated, but my intention was
> behind every single one of these enhancements."*

---

## 7. Summary of Design Authorship

Every feature in T3TR1S was initiated, scoped, and refined by the author. The
implementation was collaborative, but the vision — what to build, how it should feel,
what the edge cases should do, what the defaults should be — came from one place.

The progression from *"fix the grid lines"* to *"double points in the danger zone with
floating indicators"* is not a list of random requests. It is a coherent product being
built from the inside out: fix the fundamentals, establish the identity, design the
systems, tune the feel, then document it for the world.

That is what this project is.
