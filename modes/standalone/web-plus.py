#!/usr/bin/env python3
"""Opt-in enhanced local interface; the original web.py remains independent."""
import sys
sys.dont_write_bytecode = True
if sys.version_info < (3, 10):
    raise SystemExit('Python 3.10+ is required')
from web_plus_http import main

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    raise SystemExit(main())
