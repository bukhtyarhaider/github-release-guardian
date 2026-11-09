#!/usr/bin/env python3
"""Compatibility entrypoint for guardian.py sync; all logic remains canonical."""
import sys
from guardian.cli import main

if __name__ == "__main__":
    sys.argv.insert(1, "sync")
    raise SystemExit(main())
