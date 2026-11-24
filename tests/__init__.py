"""Test package.

The source code lives in the "src" folder (the "src layout"). This file
adds that folder to Python's import path, so the tests can run from the
project root folder with:

    python3 -m unittest discover -v

without installing the package first. (Run it from the root folder, so
Python imports "tests" as a package and executes this file first.)
"""

import os
import sys

_SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
