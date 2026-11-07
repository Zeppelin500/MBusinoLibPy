# -*- coding: utf-8 -*-
"""Test package for MBusinoLibPy.

On import ``src/`` is appended to ``sys.path`` so the tests run without
an installation - i.e. with ``python3 -m unittest`` as well as with
``python3 -m pytest`` from the repository root.
"""

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_REPO_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

#: root directory of the golden files (productions of the C++ harness)
GOLDEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden")
