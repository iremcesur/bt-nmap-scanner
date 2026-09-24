"""
Minimal stdlib test runner.

The tests are plain assert-style functions so `pytest` collects them normally,
but this repo's interpreter is an externally-managed system Python (PEP 668)
with no pytest available, so each test module also ends with

    if __name__ == "__main__":
        from _runner import run; raise SystemExit(run())

which runs the same functions using nothing but the standard library.
"""

import inspect
import sys
import traceback

import _runner_bootstrap  # noqa: F401  (sys.path setup as an import side effect)


def run(module=None):
    """Run every test_* function in `module` (default: the caller's module)."""
    if module is None:
        module = sys.modules["__main__"]
    tests = [
        (name, fn)
        for name, fn in sorted(vars(module).items())
        if name.startswith("test_") and inspect.isfunction(fn)
    ]
    failures = []
    for name, fn in tests:
        try:
            fn()
        except Exception:
            failures.append(name)
            print(f"FAIL {name}")
            traceback.print_exc()
        else:
            print(f"ok   {name}")
    print(f"\n{len(tests) - len(failures)} passed, {len(failures)} failed")
    return 1 if failures else 0
