"""Shared helper functions used by multiple engines."""
from __future__ import annotations

import random
from typing import List, Tuple


def _split_word(w: str, parts: int) -> List[str]:
    if len(w) < 2 or parts < 2:
        return [w]
    parts = min(parts, len(w))
    cuts = sorted(random.sample(range(1, len(w)), parts - 1))
    out, prev = [], 0
    for c in cuts:
        out.append(w[prev:c])
        prev = c
    out.append(w[prev:])
    return out


def _cmd_split_first(command: str) -> Tuple[str, str]:
    parts = command.strip().split(None, 1)
    if not parts:
        return "", ""
    head = parts[0]
    rest = parts[1] if len(parts) > 1 else ""
    return head, rest
