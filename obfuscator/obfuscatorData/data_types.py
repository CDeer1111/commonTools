"""Base types shared across the obfuscator package."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

CATEGORIES = ("alias", "split", "encode")


@dataclass
class ObfResult:
    category: str  # one of CATEGORIES
    code: str
    note: str = ""


class Engine:
    category: str = ""

    def generate(self, command: str, max_n: int = 5) -> List[ObfResult]:
        raise NotImplementedError
