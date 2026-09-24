"""
Puts the scanner package on sys.path.

Imported both by conftest.py (so `pytest` works) and from the top of each test
module (so `python3 tests/test_x.py` works with no pytest installed - this
repo's interpreter is an externally-managed system Python, PEP 668).
"""

import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_PYTHONFILES_DIR = os.path.abspath(
    os.path.join(_TESTS_DIR, "..", "backend", "routes", "pythonfiles")
)
for _p in (_TESTS_DIR, _PYTHONFILES_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)
