"""
Shared pytest setup for everything under Testing/.

Makes `app` importable the same way test_db.py already does by hand,
just once here instead of every test file repeating the sys.path line.
Add shared fixtures (DB session, auth tokens, etc.) here as more test
files adopt pytest.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
