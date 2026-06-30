"""Bash equivalence data and the Bash-specific obfuscation engines."""
from __future__ import annotations

import base64
import shlex
from typing import List

from .data_types import Engine, ObfResult
from .share_function import _split_word

# ===========================================================================
# Equivalence data (was data/bash.json)
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


# ===========================================================================
# Bash engines
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
