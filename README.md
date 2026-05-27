# T3TR1S  *by kakoritz*

A NES-style T3TR1S clone built from scratch in Python and Pygame.  
No image or audio assets — everything is generated procedurally at runtime.

---

## Features

- All 7 classic tetrominoes with NES-palette colours
- CW and CCW rotation with wall-kick correction
- DAS (Delayed Auto-Shift) — tap to move one, hold to slide
- Ghost piece showing landing position
- Line-clear flash animation (escalates for double / triple / Tetris)
- Particle burst on every line clear
- Screen shake on a 4-line Tetris clear
- Hard-drop impact flash
- 10-tier layered chiptune soundtrack — music builds as the game progresses, drops to a tension track when the board fills up
- Per-piece spawn tones + move / rotate / lock / hard-drop SFX
- Sidebar feedback popups: *Nice! → Great! → Fantastic! → TETRIS!* with rainbow cycling
- Pixel-art **GAME OVER** animation — block letters fall in chaos order
- High-score board — top 10 persisted to `highscores.json`, initials entry on a qualifying score
- Pause overlay — music drops to 10%, press any key to resume
- Music Preview screen — audition all 10 music tiers from the menu
- Display scale — 1× / 1.5× / 2× / 2.5× (persisted to `config.json`)

---

## Requirements

- Python 3.10+
- pygame ≥ 2.5
- numpy ≥ 1.24

---

## Installation

```bash
pip install -r requirements.txt
python3 main.py
```

---

## Controls

### Menu
| Key | Action |
|-----|--------|
| `Enter` | Start game |
| `T` | Music Preview |
| `S` | Settings |
| `H` | Leaderboard |

### Gameplay
| Key | Action |
|-----|--------|
| `←` / `→` | Move (hold for DAS auto-repeat) |
| `↑` | Rotate clockwise |
| `Ctrl+↑` or `Z` | Rotate counter-clockwise |
| `↓` | Soft drop |
| `Space` | Hard drop |
| `Q` / `Esc` | Pause |
| `R` | Restart |

### Pause
| Key | Action |
|-----|--------|
| Any key | Resume |
| `Esc` | Exit to menu |

### Music Preview
| Key | Action |
|-----|--------|
| `↑` / `↓` | Select tier |
| `Enter` or `Esc` | Back to menu |

---

## Project Structure

```
main.py           game loop, states, rendering
board.py          10×20 grid, collision, line clearing
piece.py          tetromino shapes, CW/CCW rotation
constants.py      grid sizes, colours, scoring, fall-speed curve
sprites.py        procedural NES-style block surfaces (cached)
audio.py          procedural SFX: rotate, move, lock, hard-drop, line-clears, spawns
music_game.py     10-tier layered game music (procedurally synthesised)
music.py          standalone chiptune composition
particles.py      particle burst system for line clears
game_over_anim.py pixel-art GAME OVER block-letter animation
highscore.py      JSON top-10 persistence
config.py         display-scale and settings persistence
```

---

## License

MIT — do whatever you want with it.
