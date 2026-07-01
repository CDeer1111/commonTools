#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline command obfuscator for Linux Bash, Windows CMD, and Python.

零依賴、純離線。本檔僅作為主程式入口，實際邏輯（型別、共用函式、
各平台等價資料與引擎、CLI 解析與互動選單）皆拆分於 obfuscatorData/ 套件內。

Usage:
    python obfuscator.py -p bash "cat /etc/passwd"
    python obfuscator.py -p cmd  "dir C:\\Users"
    python obfuscator.py -p auto -i
    echo "whoami" | python obfuscator.py -p bash
"""
from __future__ import annotations

import sys

from obfuscatorData.cli import main

if __name__ == "__main__":
    sys.exit(main())
