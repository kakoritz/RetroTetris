import os, sys
_ROOT = os.path.dirname(os.path.abspath(__file__))
for _d in ("core", "sounds", "render", "logic"):
    _p = os.path.join(_ROOT, _d)
    if _p not in sys.path:
        sys.path.insert(0, _p)
