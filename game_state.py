# game_state.py — per-session mutable state, reset on each new game
import pygame
from board import Board
from piece import Piece
from game_constants import SPEED_RESET_INTERVAL, NEXT_FLASH_MS


class GameState:
    """All mutable state that belongs to a single game session.

    Call reset() to start a new game. Fields are set as instance attributes
    so every function that receives a GameState can read and write them
    without nonlocal declarations.
    """

    def reset(self) -> None:
        """Initialise (or reinitialise) all per-game variables."""
        queue = [Piece() for _ in range(5)]
        self.board          = Board()
        self.current        = queue[0]
        self.piece_queue    = queue[1:]

        self.score      = 0
        self.lines      = 0
        self.level      = 1
        self.fall_timer = 0

        self.hold_piece      = None
        self.hold_used       = False

        self.lock_timer      = 0
        self.lock_move_count = 0

        self.popup_count = 0
        self.popup_timer = 0
        self.wow_active  = False

        self.last_action = 'gravity'
        self.tspin_type  = None    # 'full', 'mini', or None
        self.btb_active  = False
        self.combo       = 0
        self.combo_labels: list = []

        self.speed_tier          = 1
        self.next_speed_reset    = SPEED_RESET_INTERVAL
        self.speed_reset_count   = 0
        self.reset_bonus_mult    = 1.0
        self.full_cascade_mode   = False
        self.cascade_level       = 0
        self.first_clear_tetris  = False

        self.speed_reset_flash_timer = 0
        self.next_flash_timer        = NEXT_FLASH_MS

        self.danger_bonuses: list = []
        self.score_deltas:   list = []

        self.clear_rows:      set  = set()
        self.clear_count:     int  = 0
        self.clear_timer:     int  = 0
        self.clear_flash_idx: int  = 0
        self.clear_cells:     list = []

        self.color_clear_id       = None
        self.level_up_flash_timer = 0

        self.stat_pieces:   int   = 0
        self.stat_tetrises: int   = 0
        self.stat_tspins:   int   = 0
        self.stat_combo:    int   = 0
        self.stat_start_ms: int   = pygame.time.get_ticks()
        self.stat_time:     float = 0.0

        self.particles:      list = []
        self.shake_timer:    int  = 0
        self.hd_flash_timer: int  = 0
        self.danger:         bool = False
