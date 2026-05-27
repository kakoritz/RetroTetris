# app_state.py — application-shell state, persists across game sessions
import pygame
import config
from game_over_anim import GameOverAnim

# State machine string constants (imported here so callers can use app_state.PLAYING etc.)
MENU        = "menu"
PLAYING     = "playing"
CLEARING    = "clearing"
GAME_OVER   = "game_over"
ENTER_NAME  = "enter_name"
LEADERBOARD = "leaderboard"
SETTINGS       = "settings"
GAME_OVER_ANIM = "game_over_anim"
PAUSED         = "paused"
MUSIC_TEST     = "music_test"
CASCADING      = "cascading"


class AppState:
    """Application-level state that survives across game sessions.

    Constructed once in main(); never reset between games. Holds display
    surfaces, UI state, DAS configuration, leaderboard data, and the
    game-over animation handle.
    """

    def __init__(self, display: pygame.Surface, screen: pygame.Surface,
                 current_scale: float) -> None:
        self.display       = display
        self.screen        = screen
        self.current_scale = current_scale

        self.state: str = MENU

        # ── audio / volume ────────────────────────────────────────────────────
        self.music_vol_pct:     int = 40
        self.sfx_vol_pct:       int = 100
        self.ghost_opacity_pct: int = config.get_ghost_opacity()

        # ── settings screen ───────────────────────────────────────────────────
        self.settings_row:          int = 0
        self.settings_return_state: str = MENU

        # ── game-over animation ───────────────────────────────────────────────
        self.go_anim:         GameOverAnim = GameOverAnim()
        self.post_anim_state: str          = GAME_OVER   # ENTER_NAME or GAME_OVER

        # ── DAS / ARR ─────────────────────────────────────────────────────────
        self.das_dir:     int  = 0
        self.das_timer:   int  = 0
        self.das_charged: bool = False
        self.keys_held:   set  = set()

        _preset             = config.get_das_preset()
        self.das_preset:    str = _preset
        self.das_delay:     int = config.DAS_SETTINGS[_preset][0]
        self.das_repeat:    int = config.DAS_SETTINGS[_preset][1]

        # ── UI timers ─────────────────────────────────────────────────────────
        self.blink_timer:       int   = 0
        self.blink_on:          bool  = True
        self.pre_pause_vol:     float = 0.0
        self.cascade_anim_timer: int  = 0

        # ── music preview ─────────────────────────────────────────────────────
        self.music_test_tier: int = 1

        # ── name entry ────────────────────────────────────────────────────────
        self.initials:   list = ['A', 'A', 'A']
        self.ini_cursor: int  = 0

        # ── leaderboard ───────────────────────────────────────────────────────
        self.lb_scores:   list        = []
        self.lb_hi_name:  str | None  = None
        self.lb_hi_score: int | None  = None
        self.best:        int         = 0

        # ── debug cheat sequences ─────────────────────────────────────────────
        self._cheat_seq: list = []   # 3-2-1 WOW trigger
        self._debug_seq: list = []   # b-u-g fake crash trigger

    def reset_das(self) -> None:
        """Clear DAS state — called when a new game starts or a piece locks."""
        self.das_dir     = 0
        self.das_timer   = 0
        self.das_charged = False
        self.keys_held.clear()
