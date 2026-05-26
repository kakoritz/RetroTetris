import json
from pathlib import Path

_FILE      = Path(__file__).parent / "highscores.json"
MAX_SCORES = 10


def load() -> list[dict]:
    if not _FILE.exists():
        return []
    try:
        with _FILE.open() as f:
            return json.load(f)
    except Exception:
        return []


def qualifies(score: int) -> bool:
    if score == 0:
        return False
    scores = load()
    return len(scores) < MAX_SCORES or score > scores[-1]["score"]


def insert(name: str, score: int, lines: int, level: int) -> list[dict]:
    scores = load()
    scores.append({"name": name, "score": score, "lines": lines, "level": level})
    scores.sort(key=lambda e: e["score"], reverse=True)
    scores = scores[:MAX_SCORES]
    with _FILE.open("w") as f:
        json.dump(scores, f, indent=2)
    return scores


def best() -> int:
    scores = load()
    return scores[0]["score"] if scores else 0
