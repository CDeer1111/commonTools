"""Windows CMD equivalence data and the CMD-specific obfuscation engines."""
from __future__ import annotations

import base64
from typing import List

from .data_types import Engine, ObfResult
from .share_function import _cmd_split_first, _split_word

# ===========================================================================
# Equivalence data (was data/cmd.json)
# ===========================================================================

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
# CMD engines
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
