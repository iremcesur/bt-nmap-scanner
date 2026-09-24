"""Makes the scanner module importable when the suite is run under pytest.
The same sys.path setup lives in _runner.py for the stdlib fallback."""

import _runner_bootstrap  # noqa: F401
