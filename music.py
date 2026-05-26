"""
Procedural chiptune background loop — original composition in A minor.
Generates a temp WAV once, then streams it via pygame.mixer.music for
seamless looping. Silent no-op if numpy is unavailable.
"""
import os
import wave
import tempfile
import pygame

try:
    import numpy as np
    _HAS_NP = True
except ImportError:
    _HAS_NP = False

_RATE     = 44100
_tmp_path = None


# ── waveform helpers ──────────────────────────────────────────────────────────

def _note(freq: float, ms: int, vol: float, decay: float = 0.7):
    if freq == 0:
        return np.zeros(int(_RATE * ms / 1000))
    n    = int(_RATE * ms / 1000)
    t    = np.linspace(0, ms / 1000, n, endpoint=False)
    w    = np.sign(np.sin(2 * np.pi * freq * t)) * vol * np.exp(-decay * t)
    fade = min(int(_RATE * 0.010), n // 4)
    if fade > 0:
        ramp = 0.5 * (1 - np.cos(np.pi * np.arange(fade) / fade))
        w[:fade]  *= ramp
        w[-fade:] *= ramp[::-1]
    return w


def _build() -> np.ndarray:
    BPM   = 162
    Q     = int(60000 / BPM)   # quarter note ≈ 370 ms
    H     = Q * 2
    WHOLE = Q * 4

    V_MEL = 0.030
    V_BAS = 0.014

    # ── 4-bar melody in A minor ───────────────────────────────────────────────
    # E5  D5  C5  B4  |  A4  C5  E5  A5  |  G5  E5  D5  C5  |  B4  A4  A4..
    melody = [
        (659, Q), (587, Q), (523, Q), (494, Q),   # bar 1
        (440, Q), (523, Q), (659, Q), (880, Q),   # bar 2
        (784, Q), (659, Q), (587, Q), (523, Q),   # bar 3
        (494, Q), (440, Q), (440, H),              # bar 4  (loops → E5)
    ]

    # ── bass: one whole note per bar ─────────────────────────────────────────
    bass = [
        (110, WHOLE),   # A2
        (110, WHOLE),   # A2
        (131, WHOLE),   # C3
        (82,  WHOLE),   # E2
    ]

    mel = np.concatenate([_note(f, ms, V_MEL, 0.8) for f, ms in melody])
    bas = np.concatenate([_note(f, ms, V_BAS, 0.35) for f, ms in bass])

    n = len(mel)
    bas = bas[:n] if len(bas) >= n else np.pad(bas, (0, n - len(bas)))

    mixed = mel + bas
    peak  = np.max(np.abs(mixed))
    if peak > 0:
        mixed = mixed / peak * 0.18   # normalise, keep it background-quiet

    pcm    = (mixed * 32767).astype(np.int16)
    stereo = np.ascontiguousarray(np.column_stack([pcm, pcm]))
    return stereo


def _write_wav(data: np.ndarray, path: str) -> None:
    with wave.open(path, 'w') as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(_RATE)
        f.writeframes(data.tobytes())


# ── public API ────────────────────────────────────────────────────────────────

def start() -> None:
    global _tmp_path
    if not _HAS_NP:
        return
    try:
        if _tmp_path is None:
            stereo    = _build()
            _tmp_path = os.path.join(tempfile.gettempdir(), "nes_tetris_music.wav")
            _write_wav(stereo, _tmp_path)
        pygame.mixer.music.load(_tmp_path)
        pygame.mixer.music.set_volume(0.40)
        pygame.mixer.music.play(loops=-1)
    except Exception:
        pass   # music is optional — never crash the game


def stop() -> None:
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass
