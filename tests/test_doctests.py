# -*- coding: utf-8 -*-
"""Runs the doctest examples embedded in the source docstrings.

The examples live in the docstrings of ``MBusinoLibPy.mbusino_lib``
(``decode_telegram()``, ``get_code_units()``, ``get_device_class()``,
``get_error_message()``), so running them as a test keeps the documentation
honest: a docstring example that drifts away from the real output fails
``python3 -m unittest`` like every other test.

``python3 -m doctest`` cannot be used directly on the file, because the
package imports its siblings relatively - ``doctest.testmod()`` on the
imported module is the equivalent check.
"""

import doctest
import unittest

# src/ is already on sys.path - see tests/__init__.py
from MBusinoLibPy import mbusino_lib


class TestDoctests(unittest.TestCase):
    """Every ``>>>`` example in mbusino_lib.py must run and match."""

    def test_module_doctests(self):
        result = doctest.testmod(mbusino_lib, verbose=False)
        self.assertGreater(result.attempted, 0, "no doctest examples found")
        self.assertEqual(
            result.failed,
            0,
            "%d of %d doctest example(s) failed" % (result.failed, result.attempted),
        )


if __name__ == "__main__":
    unittest.main()
