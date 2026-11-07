# -*- coding: utf-8 -*-
"""Test-Paket für MBusinoLibPy.

Beim Import wird ``src/`` in ``sys.path`` eingehängt, damit die Tests ohne
Installation laufen - also genauso mit ``python3 -m unittest`` als auch mit
``python3 -m pytest`` aus dem Repo-Wurzelverzeichnis.
"""

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_REPO_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

#: Wurzelverzeichnis der Golden-Dateien (Erzeugnisse des C++-Harnesses)
GOLDEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden")
