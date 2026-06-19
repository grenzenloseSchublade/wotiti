import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from idle_monitor import get_idle_seconds


def test_get_idle_seconds_returns_float_or_none():
    """get_idle_seconds darf nie crashen und liefert float >= 0 oder None."""
    val = get_idle_seconds()
    assert val is None or (isinstance(val, float) and val >= 0.0)
