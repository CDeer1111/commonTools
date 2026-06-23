#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline command obfuscator (single-file edition) for Linux Bash and Windows CMD.

零依賴、純離線。將原本拆分在 engines/ 與 data/ 中的所有程式碼
與資料整合進這一個檔案,可直接執行或用 PyInstaller 打包成單一執行檔。

Usage:
    python obfuscator_all.py -p bash "cat /etc/passwd"
    python obfuscator_all.py -p cmd  "dir C:\\Users"
    python obfuscator_all.py -p auto -i
    echo "whoami" | python obfuscator_all.py -p bash

Build single binary:
    pyinstaller --onefile obfuscator_all.py
"""
from __future__ import annotations

import argparse
import base64
import json as jsonlib
import os
import random
import shlex
import sys
from dataclasses import dataclass, asdict
from typing import List, Optional

# ===========================================================================
# 1) Base types
# ===========================================================================

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


# ===========================================================================
# 2) Equivalence data (was data/*.json)
# ===========================================================================

BASH_EQUIVALENTS = {
    "cat":      ["less", "more", "tac | tac", "head -n 99999", "awk '1'", "sed -n 'p'"],
    "ls":       ["echo *", "find . -maxdepth 1 -print", "printf '%s\\n' *", "stat -c '%n' *"],
    "whoami":   ["id -un", "echo $USER", "echo $(id -un)", "logname"],
    "id":       ["whoami && groups", "echo $UID:$EUID"],
    "pwd":      ["echo $PWD", "readlink -f .", "/bin/pwd"],
    "curl":     ["wget -qO-", "fetch -qo -",
                 "python3 -c 'import sys,urllib.request as u;sys.stdout.write(u.urlopen(sys.argv[1]).read().decode())'"],
    "wget":     ["curl -O", "curl -LO"],
    "echo":     ["printf '%s\\n'", "/bin/echo"],
    "grep":     ["awk '/PATTERN/'", "sed -n '/PATTERN/p'", "rg"],
    "ps":       ["ls /proc | grep -E '^[0-9]+$'", "top -bn1"],
    "rm":       ["unlink", "find . -name NAME -delete"],
    "cp":       ["install -m644", "dd if=SRC of=DST"],
    "mv":       ["rename", "cp SRC DST && rm SRC"],
    "kill":     ["pkill -SIGTERM", "/bin/kill"],
    "uname":    ["cat /proc/version", "hostnamectl"],
    "hostname": ["cat /etc/hostname", "uname -n"],
    "ifconfig": ["ip addr", "ip a"],
    "netstat":  ["ss -tunlp", "ss -a"],
    "find":     ["locate", "ls -R"],
    "head":     ["sed -n '1,10p'", "awk 'NR<=10'"],
    "tail":     ["sed -n '$-10,$p'", "awk 'END{print}'"],
    "which":    ["command -v", "type -p"],
    "date":     ["printf '%(%c)T\\n' -1"],
    "clear":    ["printf '\\033[2J\\033[H'", "tput clear"],
}

CMD_EQUIVALENTS = {
    "dir":      ["cmd /c dir", "where /r . *", "tree /f", "powershell -c ls"],
    "type":     ["more", "powershell -c Get-Content", "find /v \"\""],
    "del":      ["erase", "powershell -c Remove-Item"],
    "erase":    ["del"],
    "copy":     ["xcopy /y", "robocopy", "powershell -c Copy-Item"],
    "move":     ["robocopy /mov", "powershell -c Move-Item"],
    "cls":      ["powershell -c clear", "powershell -c Clear-Host"],
    "echo":     ["powershell -c Write-Host", "cmd /c echo"],
    "whoami":   ["echo %USERNAME%", "powershell -c $env:USERNAME"],
    "hostname": ["echo %COMPUTERNAME%", "powershell -c hostname"],
    "ipconfig": ["powershell -c Get-NetIPAddress", "wmic nicconfig get IPAddress"],
    "tasklist": ["powershell -c Get-Process", "wmic process list brief"],
    "taskkill": ["powershell -c Stop-Process", "wmic process where name='X' delete"],
    "find":     ["findstr", "powershell -c Select-String"],
    "ping":     ["powershell -c Test-Connection"],
    "ver":      ["powershell -c [Environment]::OSVersion"],
    "set":      ["powershell -c Get-ChildItem env:"],
    "where":    ["powershell -c Get-Command"],
    "mkdir":    ["md", "powershell -c New-Item -ItemType Directory"],
    "rmdir":    ["rd", "powershell -c Remove-Item -Recurse"],
    "cd":       ["chdir", "pushd"],
}


# ===========================================================================
# 3) Shared helpers
# ===========================================================================

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


def _cmd_split_first(command: str):
    parts = command.strip().split(None, 1)
    if not parts:
        return "", ""
    head = parts[0]
    rest = parts[1] if len(parts) > 1 else ""
    return head, rest


# ===========================================================================
# 4) Bash engines
# ===========================================================================

class BashAliasEngine(Engine):
    category = "alias"

    def generate(self, command: str, max_n: int = 5) -> List[ObfResult]:
        try:
            tokens = shlex.split(command, posix=True)
        except ValueError:
            tokens = command.split()
        if not tokens:
            return []
        head, rest = tokens[0], tokens[1:]
        equivs = BASH_EQUIVALENTS.get(head, [])
        rest_str = (" " + " ".join(shlex.quote(t) for t in rest)) if rest else ""
        out: List[ObfResult] = []
        for eq in equivs[:max_n]:
            out.append(ObfResult("alias", f"{eq}{rest_str}", f"{head} → {eq}"))
        if len(out) < max_n:
            out.append(ObfResult("alias", f"$(which {head}){rest_str}", "use absolute resolution"))
        return out[:max_n]


class BashSplitEngine(Engine):
    category = "split"

    def generate(self, command: str, max_n: int = 5) -> List[ObfResult]:
        try:
            tokens = shlex.split(command, posix=True)
        except ValueError:
            tokens = command.split()
        if not tokens:
            return []
        head, rest = tokens[0], tokens[1:]
        rest_str = (" " + " ".join(shlex.quote(t) for t in rest)) if rest else ""
        results: List[ObfResult] = []

        pieces = _split_word(head, 2)
        if len(pieces) >= 2:
            assigns = ";".join(f"{chr(ord('a')+i)}={p}" for i, p in enumerate(pieces))
            refs = "".join(f"${chr(ord('a')+i)}" for i in range(len(pieces)))
            results.append(ObfResult("split", f"{assigns};{refs}{rest_str}", "variable concat"))

        pieces3 = _split_word(head, 3)
        if len(pieces3) >= 2:
            assigns = ";".join(f"{chr(ord('a')+i)}={p}" for i, p in enumerate(pieces3))
            refs = "".join(f"${chr(ord('a')+i)}" for i in range(len(pieces3)))
            results.append(ObfResult("split", f"{assigns};{refs}{rest_str}", "3-piece split"))

        if len(head) >= 2:
            i = len(head) // 2
            injected = head[:i] + '""' + head[i:]
            results.append(ObfResult("split", f'{injected}{rest_str}', "empty quote injection"))

        esc = "".join("\\" + c if c.isalpha() else c for c in head)
        results.append(ObfResult("split", f"{esc}{rest_str}", "backslash escape"))

        if rest:
            ifs_cmd = "${IFS}".join([head] + [shlex.quote(t) for t in rest])
            results.append(ObfResult("split", f'eval "{ifs_cmd}"', "${IFS} separators"))
        else:
            results.append(ObfResult("split", f'eval "{head}"', "eval wrap"))

        return results[:max_n]


class BashEncodeEngine(Engine):
    category = "encode"

    def generate(self, command: str, max_n: int = 5) -> List[ObfResult]:
        results: List[ObfResult] = []

        b64 = base64.b64encode(command.encode()).decode()
        results.append(ObfResult("encode", f"echo {b64} | base64 -d | bash", "base64 → bash"))

        hexs = command.encode().hex()
        results.append(ObfResult("encode", f'eval "$(echo {hexs} | xxd -r -p)"', "hex → eval"))

        printf_x = "".join(f"\\x{b:02x}" for b in command.encode())
        results.append(ObfResult("encode", f"bash -c \"$(printf '{printf_x}')\"", "printf \\x → bash"))

        oct_esc = "".join(f"\\{b:03o}" for b in command.encode())
        results.append(ObfResult("encode", f"eval $'{oct_esc}'", "octal $'...' → eval"))

        rev = command[::-1]
        results.append(ObfResult("encode", f'eval "$(echo "{rev}" | rev)"', "string reverse"))

        return results[:max_n]


# ===========================================================================
# 5) CMD engines
# ===========================================================================

class CmdAliasEngine(Engine):
    category = "alias"

    def generate(self, command: str, max_n: int = 5) -> List[ObfResult]:
        head, rest = _cmd_split_first(command)
        if not head:
            return []
        equivs = CMD_EQUIVALENTS.get(head.lower(), [])
        rest_str = (" " + rest) if rest else ""
        out: List[ObfResult] = []
        for eq in equivs[:max_n]:
            out.append(ObfResult("alias", f"{eq}{rest_str}", f"{head} → {eq}"))
        if len(out) < max_n:
            out.append(ObfResult("alias", f"cmd /c {command}", "wrap in cmd /c"))
        return out[:max_n]


class CmdSplitEngine(Engine):
    category = "split"

    def generate(self, command: str, max_n: int = 5) -> List[ObfResult]:
        head, rest = _cmd_split_first(command)
        if not head:
            return []
        rest_str = (" " + rest) if rest else ""
        results: List[ObfResult] = []

        pieces = _split_word(head, 2)
        if len(pieces) >= 2:
            assigns = " & ".join(f"set {chr(ord('a')+i)}={p}" for i, p in enumerate(pieces))
            refs = "".join(f"%{chr(ord('a')+i)}%" for i in range(len(pieces)))
            results.append(ObfResult("split", f"{assigns} & call {refs}{rest_str}", "set/call concat"))

        pieces3 = _split_word(head, 3)
        if len(pieces3) >= 2:
            assigns = " & ".join(f"set {chr(ord('a')+i)}={p}" for i, p in enumerate(pieces3))
            refs = "".join(f"%{chr(ord('a')+i)}%" for i in range(len(pieces3)))
            results.append(ObfResult("split", f"{assigns} & call {refs}{rest_str}", "3-piece set/call"))

        esc = "^".join(head)
        results.append(ObfResult("split", f"{esc}{rest_str}", "caret escape"))

        if len(head) >= 2:
            i = len(head) // 2
            results.append(ObfResult("split", f'{head[:i]}""{head[i:]}{rest_str}', "empty quote injection"))

        results.append(ObfResult(
            "split",
            f'for /f "delims=" %i in (\'echo {command}\') do %i',
            "for /f indirection",
        ))

        return results[:max_n]


class CmdEncodeEngine(Engine):
    category = "encode"

    def generate(self, command: str, max_n: int = 5) -> List[ObfResult]:
        results: List[ObfResult] = []

        ps_payload = base64.b64encode(command.encode("utf-16le")).decode()
        results.append(ObfResult(
            "encode",
            f"powershell -NoP -NonI -EncodedCommand {ps_payload}",
            "PowerShell -EncodedCommand (UTF-16LE)",
        ))

        utf8_b64 = base64.b64encode(command.encode("utf-8")).decode()
        results.append(ObfResult(
            "encode",
            f"powershell -NoP -c \"iex ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{utf8_b64}')))\"",
            "PowerShell IEX base64",
        ))

        results.append(ObfResult(
            "encode",
            f"echo {utf8_b64}> p.b64 & certutil -decode p.b64 p.bat & call p.bat & del p.b64 p.bat",
            "certutil -decode loader",
        ))

        hexs = command.encode().hex()
        results.append(ObfResult(
            "encode",
            f"powershell -NoP -c \"iex ([Text.Encoding]::UTF8.GetString(([byte[]] -split ('{hexs}' -replace '..','0x$& ')) ))\"",
            "PowerShell hex → IEX",
        ))

        chars = ",".join(str(ord(c)) for c in command)
        results.append(ObfResult(
            "encode",
            f"powershell -NoP -c \"iex (-join ({chars} | %{{[char]$_}}))\"",
            "PowerShell char-code → IEX",
        ))

        return results[:max_n]


# ===========================================================================
# 5b) Python engines
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
    import re
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
        import re
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


# ===========================================================================
# 6) Dispatcher / CLI
# ===========================================================================

ENGINES = {
    "bash":   [BashAliasEngine(),   BashSplitEngine(),   BashEncodeEngine()],
    "cmd":    [CmdAliasEngine(),    CmdSplitEngine(),    CmdEncodeEngine()],
    "python": [PythonAliasEngine(), PythonSplitEngine(), PythonEncodeEngine()],
}

CATEGORY_TITLE = {
    "alias":  "別名/等價替換 (Alias / Equivalent)",
    "split":  "字串拆分與變數組合 (Split / Variable Concat)",
    "encode": "編碼混淆 (Encoding)",
}

ANSI = {
    "reset":  "\033[0m",
    "bold":   "\033[1m",
    "cyan":   "\033[36m",
    "yellow": "\033[33m",
    "green":  "\033[32m",
    "dim":    "\033[2m",
}


def auto_platform() -> str:
    return "cmd" if os.name == "nt" else "bash"


def run(command: str, platform: str, only: Optional[str], max_n: int) -> List[ObfResult]:
    results: List[ObfResult] = []
    for engine in ENGINES[platform]:
        if only and engine.category != only:
            continue
        results.extend(engine.generate(command, max_n=max_n))
    return results


def render_text(command: str, platform: str, results: List[ObfResult], color: bool) -> str:
    c = ANSI if color else {k: "" for k in ANSI}
    lines = [
        f"{c['bold']}[原始 / Original]{c['reset']} ({platform})  {c['cyan']}{command}{c['reset']}",
        "",
    ]
    n = 1
    for cat in CATEGORIES:
        bucket = [r for r in results if r.category == cat]
        if not bucket:
            continue
        lines.append(f"{c['bold']}{c['yellow']}== {CATEGORY_TITLE[cat]} =={c['reset']}")
        for r in bucket:
            note = f"  {c['dim']}# {r.note}{c['reset']}" if r.note else ""
            lines.append(f"  {c['green']}{n:>2}){c['reset']} {r.code}{note}")
            n += 1
        lines.append("")
    if n == 1:
        lines.append("(no obfuscations produced — unknown command head?)")
    return "\n".join(lines)


def parse_args(argv):
    p = argparse.ArgumentParser(description="Offline command obfuscator (Bash / CMD / Python) — single file")
    p.add_argument("command", nargs="?", help="Command to obfuscate (omit to read stdin, -f, or use -i)")
    p.add_argument("-p", "--platform", choices=["bash", "cmd", "python", "auto"], default="auto")
    p.add_argument("-i", "--interactive", action="store_true", help="Interactive REPL")
    p.add_argument("-f", "--file", help="Read commands / code from a file and obfuscate its contents")
    p.add_argument("--whole", action="store_true",
                   help="Treat file content as ONE block (auto-on for python or .py files)")
    p.add_argument("-o", "--output", help="Write results to this file instead of stdout")
    p.add_argument("--only", choices=list(CATEGORIES), help="Show only one category")
    p.add_argument("--max", type=int, default=5, dest="max_n", help="Max variants per category (default 5)")
    p.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    return p.parse_args(argv)


def _resolve_platform(cmd: str, args) -> str:
    if args.platform != "auto":
        return args.platform
    if args.file and args.file.endswith(".py"):
        return "python"
    if "\n" in cmd:
        return "python"
    return auto_platform()


def _render_once(cmd: str, args) -> str:
    platform = _resolve_platform(cmd, args)
    results = run(cmd, platform, args.only, args.max_n)
    if args.json:
        return jsonlib.dumps({
            "original": cmd,
            "platform": platform,
            "results": [asdict(r) for r in results],
        }, ensure_ascii=False, indent=2)
    color = (not args.no_color) and sys.stdout.isatty() and not args.output
    return render_text(cmd, platform, results, color)


def process_once(cmd: str, args) -> None:
    out = _render_once(cmd, args)
    if args.output:
        with open(args.output, "a", encoding="utf-8") as fh:
            fh.write(out + "\n\n")
    else:
        print(out)


def _iter_file_blocks(path: str, platform_hint: str, whole: bool):
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    treat_whole = whole or platform_hint == "python" or (platform_hint == "auto" and path.endswith(".py"))
    if treat_whole:
        text = content.rstrip("\n")
        if text:
            yield text
        return
    for raw in content.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith("::") or line.lower().startswith("rem "):
            continue
        yield line


def main(argv=None) -> int:
    args = parse_args(argv)

    if args.output:
        # truncate so each run starts clean
        open(args.output, "w", encoding="utf-8").close()

    if args.interactive:
        platform = auto_platform() if args.platform == "auto" else args.platform
        print(f"obfuscator REPL ({platform}) — Ctrl-D / Ctrl-C to exit")
        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if not line:
                continue
            process_once(line, args)
        return 0

    if args.file:
        if not os.path.isfile(args.file):
            print(f"error: file not found: {args.file}", file=sys.stderr)
            return 2
        count = 0
        for block in _iter_file_blocks(args.file, args.platform, args.whole):
            process_once(block, args)
            count += 1
        if count == 0:
            print("error: no runnable content found in file.", file=sys.stderr)
            return 2
        if args.output:
            print(f"wrote {count} obfuscation block(s) to {args.output}")
        return 0

    if args.command:
        process_once(args.command, args)
        return 0

    if not sys.stdin.isatty():
        data = sys.stdin.read().strip()
        if data:
            for line in data.splitlines():
                line = line.strip()
                if line:
                    process_once(line, args)
            return 0

    print("error: no command provided. Pass as argument, use -f FILE, pipe stdin, or use -i.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
