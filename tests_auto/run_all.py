#!/usr/bin/env python3
import importlib
import sys
from pathlib import Path

# Ensure project root is on sys.path (so "tests_auto.*" imports work)
ROOT = Path("/opt/oss-migrate/llm-planner")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_MODULES = [
    "tests_auto.test_rule1",
    "tests_auto.test_rule2",
    "tests_auto.test_rule3",
    "tests_auto.test_rule4",
    "tests_auto.test_rule5",
    "tests_auto.test_rule6",
    "tests_auto.test_rule7",
    "tests_auto.test_strikethrough",  # best-effort only
]

def main():
    failed = []
    for mod_name in TEST_MODULES:
        try:
            mod = importlib.import_module(mod_name)
            # each module runs tests if called as __main__; we call functions directly if present
            # For simplicity: run module-level functions starting with "test_"
            test_fns = [getattr(mod, n) for n in dir(mod) if n.startswith("test_") and callable(getattr(mod, n))]
            for fn in test_fns:
                fn()
            print(f"[OK] {mod_name}")
        except Exception as e:
            print(f"[FAIL] {mod_name}: {e}")
            failed.append((mod_name, str(e)))

    print("")
    if failed:
        print("FAILED TESTS:")
        for m, err in failed:
            print(f" - {m}: {err}")
        sys.exit(1)

    print("ALL TESTS PASSED")
    sys.exit(0)

if __name__ == "__main__":
    main()
