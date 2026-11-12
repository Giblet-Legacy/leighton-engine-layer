"""
conftest.py — pytest path setup for P14 Leighton Engine

Function:
    Puts the sibling P10 and P11 repositories (../weight-layer and
    ../trust-layer) on sys.path, resolved relative to this file rather
    than the current working directory, so `pytest` works from any
    directory. v1 leighton_engine.py and test_leighton_engine.py
    resolve the paths against the CWD and are frozen; this file is the
    layer that fixes that without editing them.
"""

import os
import sys

# ---------------------------------------------------------------------------
# 1. Module-level path setup
#    Runs once when pytest loads this conftest, before test collection.
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
for _name in ("trust-layer", "weight-layer"):
    _path = os.path.normpath(os.path.join(_HERE, "..", _name))
    if _path not in sys.path:
        sys.path.insert(0, _path)
