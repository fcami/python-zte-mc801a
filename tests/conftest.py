"""Stub missing optional runtime deps so daemon can be imported in tests."""

import sys
import types

if "retry" not in sys.modules:
    stub = types.ModuleType("retry")
    stub.retry = lambda *a, **kw: (lambda f: f)  # no-op decorator
    sys.modules["retry"] = stub
