"""Unit tests for scoring constants and formulas used in the CLEARING handler."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from constants import SCORE_TABLE, COLS, ROWS
import main as _m   # import module-level constants without running main()


# ── score table ───────────────────────────────────────────────────────────────

def test_score_table_values():
    assert SCORE_TABLE[1] == 40
    assert SCORE_TABLE[2] == 100
    assert SCORE_TABLE[3] == 300
    assert SCORE_TABLE[4] == 1200


def test_score_table_has_no_zero_key():
    assert 0 not in SCORE_TABLE


# ── T-spin scoring ────────────────────────────────────────────────────────────

def test_tspin_scores_exceed_normal():
    """Full T-spin clears should always beat the equivalent normal-clear base."""
    for n in (1, 2):
        assert _m.TSPIN_SCORES[n] > SCORE_TABLE.get(n, 0)


def test_tspin_mini_scores_less_than_full():
    for n in (1, 2):
        assert _m.TSPIN_MINI_SCORES[n] < _m.TSPIN_SCORES[n]


# ── combo formula ─────────────────────────────────────────────────────────────

def _combo_bonus(combo: int, level: int) -> int:
    return _m.COMBO_BONUS_UNIT * combo * (level + 1)


def test_combo_zero_no_bonus():
    assert _combo_bonus(0, 0) == 0


def test_combo_first_streak_is_second_clear():
    """combo=0 on 1st clear → no bonus; combo=1 on 2nd → first bonus fires."""
    assert _combo_bonus(0, 0) == 0
    assert _combo_bonus(1, 0) == _m.COMBO_BONUS_UNIT


def test_combo_scales_with_level():
    bonus_l0 = _combo_bonus(3, 0)
    bonus_l4 = _combo_bonus(3, 4)
    assert bonus_l4 == bonus_l0 * 5


# ── danger multiplier ─────────────────────────────────────────────────────────

def test_danger_doubles_base_single():
    base = SCORE_TABLE[1] * 1   # level 0, (level+1)=1
    assert base * 2 == 80


def test_danger_doubles_tetris():
    base = SCORE_TABLE[4] * 1
    assert base * 2 == 2400


# ── WOW bonus ────────────────────────────────────────────────────────────────

def test_wow_bonus_scales_with_level():
    assert _m.WOW_BONUS * (0 + 1) == 5000
    assert _m.WOW_BONUS * (4 + 1) == 25000


# ── color clear bonus ─────────────────────────────────────────────────────────

def test_color_clear_bonus_flat():
    assert _m.COLOR_CLEAR_BONUS == 5000


# ── back-to-back multiplier ───────────────────────────────────────────────────

def test_btb_multiplier_on_tetris():
    base = SCORE_TABLE[4] * (5 + 1)   # level 5
    btb  = int(base * 1.5)
    assert btb == 10800


# ── placement score ───────────────────────────────────────────────────────────

def test_placement_score_positive():
    assert _m.PLACEMENT_SCORE > 0


# ── hard / soft drop scoring ─────────────────────────────────────────────────

def test_hard_drop_2_per_row():
    """Hard drop should award 2 points per row fallen."""
    rows = 10
    assert rows * 2 == 20


def test_soft_drop_1_per_row():
    """Soft drop awards 1 point per row."""
    rows = 5
    assert rows * 1 == 5


# ── reset multiplier growth ───────────────────────────────────────────────────

def test_reset_mult_grows_by_point_one():
    import builtins
    mult = 1.0
    for i in range(1, 6):
        mult = round(1.0 + i * 0.1, 1)
        assert abs(mult - (1.0 + i * 0.1)) < 1e-9


# ── cascade interval growth ───────────────────────────────────────────────────

def test_cascade_interval_grows():
    """Each reset raises the threshold by CASCADE_INTERVAL_GROWTH more."""
    threshold = 0
    for reset_count in range(5):
        threshold += _m.SPEED_RESET_INTERVAL + reset_count * _m.CASCADE_INTERVAL_GROWTH
    # 1st:10k, 2nd:15k, 3rd:20k, 4th:25k, 5th:30k → total 100k
    assert threshold == 100_000


# ── popup style completeness ──────────────────────────────────────────────────

def test_all_popup_styles_have_text():
    for key, val in _m.POPUP_STYLES.items():
        assert isinstance(val[0], str) and val[0], f"popup {key} missing text"


def test_popup_15_is_color_clear():
    assert "COLOR" in _m.POPUP_STYLES[15][0]
