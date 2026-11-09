#!/usr/bin/env python3
"""Compatibility entrypoint for guardian.py validate-release; all logic remains canonical."""
import sys
from guardian.cli import main

if __name__ == "__main__":
    sys.argv.insert(1, "validate-release")
    raise SystemExit(main())
