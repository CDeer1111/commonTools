"""Python equivalence data and the Python-specific obfuscation engines."""
from __future__ import annotations

import base64
import re
from typing import List, Optional

from .data_types import Engine, ObfResult
from .share_function import _split_word

# ===========================================================================
# Equivalence data (was data/python.json)
# ===========================================================================

PYTHON_EQUIVALENTS = {
    # 常見呼叫的等價寫法。鍵會以「整段字串包含」方式比對,寫法保留 {arg} 佔位。
    # 若找不到任何鍵命中,Alias 引擎會回退到 exec/compile 包裝。
    "print(":        ["__import__('sys').stdout.write(str({arg})+'\\n')",
                      "getattr(__builtins__,'print')({arg})"],
    "input(":        ["__import__('sys').stdin.readline().rstrip('\\n')"],
    "open(":         ["__import__('io').open({arg})", "__import__('builtins').open({arg})"],
    "len(":          ["{arg}.__len__()"],
    "range(":        ["__import__('builtins').range({arg})"],
    "str(":          ["{arg}.__str__()", "'%s'%({arg},)"],
    "int(":          ["__import__('builtins').int({arg})"],
    "list(":         ["[*({arg})]"],
    "dict(":         ["{{**({arg})}}"],
    "type(":         ["{arg}.__class__"],
    "exit(":         ["__import__('sys').exit({arg})"],
    "os.system(":    ["__import__('os').system({arg})",
                      "__import__('subprocess').call({arg}, shell=True)"],
    "os.popen(":     ["__import__('subprocess').check_output({arg}, shell=True)"],
    "subprocess.run(":["__import__('subprocess').run({arg})"],
    "import ":       ["__import__('{arg}')"],
}


def _py_find_key(code: str, key: str) -> int:
    """Word-boundary find of `key` in `code`. Return -1 if not found."""
    # 對於以 '(' 結尾的呼叫,要求識別字前面不是 [A-Za-z0-9_.]
    if key.endswith("("):
        pat = r"(?<![A-Za-z0-9_.])" + re.escape(key)
    else:
        pat = r"(?<![A-Za-z0-9_])" + re.escape(key)
    m = re.search(pat, code)
    return m.start() if m else -1


def _py_extract_arg(code: str, key: str) -> Optional[str]:
    """從 code 中找到 key( ... ) 並回傳括號內字串(粗略,逐層計數)。"""
    idx = _py_find_key(code, key)
    if idx < 0:
        return None
    if not key.endswith("("):
        rest = code[idx + len(key):].strip()
        if not rest:
            return None
        # 取直到 ; 或空白為止的識別字
        m = re.match(r"[A-Za-z0-9_.]+", rest)
        return m.group(0) if m else None
    start = idx + len(key)
    depth = 1
    i = start
    while i < len(code) and depth > 0:
        ch = code[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return code[start:i]
        i += 1
    return None


# ===========================================================================
# Python engines
# ===========================================================================

class PythonAliasEngine(Engine):
    category = "alias"

    def generate(self, command: str, max_n: int = 5) -> List[ObfResult]:
        out: List[ObfResult] = []
        for key, repls in PYTHON_EQUIVALENTS.items():
            if _py_find_key(command, key) < 0:
                continue
            arg = _py_extract_arg(command, key)
            if arg is None:
                continue
            for tpl in repls:
                new_call = tpl.format(arg=arg)
                if key.endswith("("):
                    full = key + arg + ")"
                    out.append(ObfResult("alias",
                                         command.replace(full, new_call, 1),
                                         f"{key.rstrip('(')} → {tpl.split('(')[0]}"))
                else:
                    full = key + arg
                    out.append(ObfResult("alias",
                                         command.replace(full, new_call, 1),
                                         f"{key.strip()} → __import__"))
                if len(out) >= max_n:
                    return out
        # fallback wrappers
        out.append(ObfResult("alias",
                             f"exec(compile({command!r},'<s>','exec'))",
                             "exec(compile(...))"))
        out.append(ObfResult("alias",
                             f"eval(compile({command!r},'<s>','exec'))",
                             "eval(compile(...,'exec'))"))
        out.append(ObfResult("alias",
                             f"__import__('builtins').exec({command!r})",
                             "__import__ → exec"))
        return out[:max_n]


class PythonSplitEngine(Engine):
    category = "split"

    def generate(self, command: str, max_n: int = 5) -> List[ObfResult]:
        results: List[ObfResult] = []

        # 1) 把整段 source 拆成 2 段字串相加後 exec
        if len(command) >= 2:
            mid = len(command) // 2
            a, b = command[:mid], command[mid:]
            results.append(ObfResult(
                "split",
                f"_a={a!r};_b={b!r};exec(_a+_b)",
                "2-piece string concat → exec",
            ))

        # 2) 拆成 3 段
        if len(command) >= 3:
            pieces = _split_word(command, 3)
            assigns = ";".join(f"_{chr(ord('a')+i)}={p!r}" for i, p in enumerate(pieces))
            joined = "+".join(f"_{chr(ord('a')+i)}" for i in range(len(pieces)))
            results.append(ObfResult("split", f"{assigns};exec({joined})", "3-piece concat → exec"))

        # 3) list + join
        results.append(ObfResult(
            "split",
            f"exec(''.join({list(command)!r}))",
            "char list → join → exec",
        ))

        # 4) 反轉後 exec
        results.append(ObfResult(
            "split",
            f"exec({command[::-1]!r}[::-1])",
            "reverse string → exec",
        ))

        # 5) 用 chr() 重建關鍵字串中的某些字元
        if len(command) >= 4:
            i = len(command) // 2
            mid_ch = command[i]
            mutated = command[:i] + "\x00" + command[i + 1:]
            results.append(ObfResult(
                "split",
                f"exec({mutated!r}.replace(chr(0),chr({ord(mid_ch)})))",
                "chr() injection",
            ))

        return results[:max_n]


class PythonEncodeEngine(Engine):
    category = "encode"

    def generate(self, command: str, max_n: int = 5) -> List[ObfResult]:
        results: List[ObfResult] = []
        raw = command.encode("utf-8")

        b64 = base64.b64encode(raw).decode()
        results.append(ObfResult(
            "encode",
            f"import base64;exec(base64.b64decode('{b64}'))",
            "base64 → exec",
        ))

        results.append(ObfResult(
            "encode",
            f"exec(__import__('base64').b64decode('{b64}'))",
            "base64 + __import__ → exec (one-liner)",
        ))

        import zlib
        z = base64.b64encode(zlib.compress(raw)).decode()
        results.append(ObfResult(
            "encode",
            f"import base64,zlib;exec(zlib.decompress(base64.b64decode('{z}')))",
            "zlib + base64 → exec",
        ))

        hexs = raw.hex()
        results.append(ObfResult(
            "encode",
            f"exec(bytes.fromhex('{hexs}').decode())",
            "hex → exec",
        ))

        try:
            import codecs
            rot = codecs.encode(command, "rot_13")
            results.append(ObfResult(
                "encode",
                f"import codecs;exec(codecs.decode({rot!r},'rot_13'))",
                "rot13 → exec (僅 ASCII 字母被換)",
            ))
        except Exception:
            pass

        escs = "".join(f"\\x{b:02x}" for b in raw)
        results.append(ObfResult(
            "encode",
            f"exec(\"{escs}\")",
            "\\xNN escape → exec",
        ))

        return results[:max_n]
