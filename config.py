import json
from pathlib import Path

_FILE = Path(__file__).parent / "config.json"

_DEFAULTS = {"scale": 1.5, "ghost_opacity": 25}

VALID_SCALES = [1.0, 1.5, 2.0, 2.5]


def load() -> dict:
    if not _FILE.exists():
        return dict(_DEFAULTS)
    try:
        data = json.loads(_FILE.read_text())
        # Clamp scale to a valid value
        s = data.get("scale", _DEFAULTS["scale"])
        if s not in VALID_SCALES:
            s = min(VALID_SCALES, key=lambda v: abs(v - s))
        data["scale"] = s
        # Clamp ghost opacity to 0-100
        data["ghost_opacity"] = max(0, min(100, int(
            data.get("ghost_opacity", _DEFAULTS["ghost_opacity"]))))
        return data
    except Exception:
        return dict(_DEFAULTS)


def save(data: dict) -> None:
    try:
        _FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def get_scale() -> float:
    return load()["scale"]


def set_scale(s: float) -> None:
    data = load()
    data["scale"] = s
    save(data)


def get_ghost_opacity() -> int:
    return load()["ghost_opacity"]


def set_ghost_opacity(pct: int) -> None:
    data = load()
    data["ghost_opacity"] = max(0, min(100, int(pct)))
    save(data)
