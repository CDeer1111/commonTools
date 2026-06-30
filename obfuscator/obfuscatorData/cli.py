"""CLI argument parsing, rendering, dispatcher, and interactive menu."""
from __future__ import annotations

import json as jsonlib
import os
import sys
from dataclasses import asdict
from typing import List, Optional

from .data_bash import BashAliasEngine, BashEncodeEngine, BashSplitEngine
from .data_python import PythonAliasEngine, PythonEncodeEngine, PythonSplitEngine
from .data_types import CATEGORIES, ObfResult
from .data_windows import CmdAliasEngine, CmdEncodeEngine, CmdSplitEngine

# ===========================================================================
# Dispatcher
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


# ===========================================================================
# Argument parsing
# ===========================================================================

def parse_args(argv):
    import argparse
    p = argparse.ArgumentParser(description="離線指令混淆工具（Bash / CMD / Python）— 拆分套件版")
    p.add_argument("command", nargs="?", help="要混淆的指令（省略則從標準輸入讀取，或使用 -f / -i）")
    p.add_argument("-p", "--platform", choices=["bash", "cmd", "python", "auto"], default="auto",
                   help="目標平台（預設：auto）")
    p.add_argument("-i", "--interactive", action="store_true", help="進入互動式選單界面")
    p.add_argument("-f", "--file", help="從檔案讀取指令或程式碼並進行混淆")
    p.add_argument("--whole", action="store_true",
                   help="將檔案內容視為單一整體處理（Python 或 .py 檔案時自動啟用）")
    p.add_argument("-o", "--output", help="將結果寫入指定檔案而非標準輸出")
    p.add_argument("--only", choices=list(CATEGORIES), help="只顯示特定類別的混淆結果")
    p.add_argument("--max", type=int, default=5, dest="max_n", help="每個類別最多顯示幾種變體（預設：5）")
    p.add_argument("--json", action="store_true", help="以 JSON 格式輸出（便於程式讀取）")
    p.add_argument("--no-color", action="store_true", help="停用 ANSI 色彩輸出")
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


# ===========================================================================
# Interactive menu
# ===========================================================================

def _choose(prompt: str, options: list, allow_back: bool = False) -> Optional[int]:
    """顯示編號選單，回傳選擇的索引 (0-based)；回傳 None 表示返回/取消。"""
    c = ANSI if sys.stdout.isatty() else {k: "" for k in ANSI}
    for i, opt in enumerate(options, 1):
        print(f"  {c['green']}{i}{c['reset']}) {opt}")
    if allow_back:
        print(f"  {c['yellow']}0{c['reset']}) 返回上一步")
    print()
    while True:
        try:
            raw = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if raw == "":
            continue
        if allow_back and raw == "0":
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        lo = 1
        hi = len(options)
        print(f"  請輸入 {lo}–{hi} 之間的數字{', 或 0 返回' if allow_back else ''}。")


def _interactive_menu(args) -> None:
    """全繁體中文數字選單互動界面。"""
    c = ANSI if sys.stdout.isatty() else {k: "" for k in ANSI}

    PLATFORM_NAMES = ["Bash (Linux/macOS)", "CMD (Windows)", "Python"]
    PLATFORM_KEYS  = ["bash", "cmd", "python"]

    INPUT_NAMES = ["直接輸入指令", "從檔案讀取"]

    print(f"\n{c['bold']}{c['cyan']}=== 指令混淆工具 ==={c['reset']}\n")

    # ── 步驟 1：選擇平台 ──────────────────────────────────────────────────
    while True:
        print(f"{c['bold']}【步驟 1】選擇平台模式{c['reset']}")
        if args.platform != "auto":
            default_idx = PLATFORM_KEYS.index(args.platform)
            PLATFORM_NAMES[default_idx] += f"  {c['dim']}(預設){c['reset']}"
        plat_idx = _choose("請選擇平台編號：", PLATFORM_NAMES)
        if plat_idx is None:
            print("已離開。")
            return
        platform = PLATFORM_KEYS[plat_idx]

        # ── 步驟 2：選擇輸入方式 ──────────────────────────────────────────
        print(f"\n{c['bold']}【步驟 2】選擇輸入方式{c['reset']}")
        input_idx = _choose("請選擇輸入方式編號：", INPUT_NAMES, allow_back=True)
        if input_idx is None:
            # 返回步驟 1
            print()
            continue

        # ── 取得指令 ──────────────────────────────────────────────────────
        if input_idx == 0:
            # 直接輸入（支援多行，整體一起混淆）
            print(f"\n{c['bold']}【步驟 3】輸入指令{c['reset']}")
            print(f"  {c['dim']}支援多行輸入；輸入完畢後連按兩次 Enter 確認，Ctrl-C 返回上一步{c['reset']}")
            lines = []
            try:
                while True:
                    row = input("" if lines else "請輸入指令：")
                    if row == "" and lines and lines[-1] == "":
                        break
                    lines.append(row)
            except (EOFError, KeyboardInterrupt):
                print()
                continue
            # 去掉結尾空行
            while lines and lines[-1] == "":
                lines.pop()
            block = "\n".join(lines).strip()
            if not block:
                print("  指令不可為空，請重試。\n")
                continue
            # 整段當作一個混淆單位
            commands = [block]
            is_file = False
        else:
            # 從檔案讀取
            print(f"\n{c['bold']}【步驟 3】輸入檔案路徑{c['reset']}")
            print(f"  {c['dim']}(按 Ctrl-C 可返回){c['reset']}")
            try:
                filepath = input("請輸入檔案路徑：").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                continue
            if not filepath or not os.path.isfile(filepath):
                print(f"  找不到檔案：{filepath}\n")
                continue
            whole = args.whole or platform == "python" or filepath.endswith(".py")
            commands = list(_iter_file_blocks(filepath, platform, whole))
            if not commands:
                print("  檔案中找不到可執行的內容。\n")
                continue
            is_file = True

        # ── 步驟 4：產生並列出所有結果 ────────────────────────────────────
        while True:
            all_results: List[ObfResult] = []
            for cmd in commands:
                all_results.extend(run(cmd, platform, args.only, args.max_n))

            if not all_results:
                print(f"\n  {c['yellow']}（此指令/平台組合未產生任何混淆結果）{c['reset']}\n")
                break

            # 顯示所有結果（含分類標題）
            print(f"\n{c['bold']}【步驟 4】混淆結果列表{c['reset']}")
            # 顯示原始指令
            orig_display = commands[0] if len(commands) == 1 else f"({len(commands)} 行)"
            print(f"  原始指令：{c['cyan']}{orig_display}{c['reset']}  平台：{platform}\n")

            # 建立編號對照表
            numbered: List[ObfResult] = []
            n = 1
            for cat in CATEGORIES:
                bucket = [r for r in all_results if r.category == cat]
                if not bucket:
                    continue
                print(f"  {c['bold']}{c['yellow']}── {CATEGORY_TITLE[cat]} ──{c['reset']}")
                for r in bucket:
                    note = f"  {c['dim']}# {r.note}{c['reset']}" if r.note else ""
                    print(f"    {c['green']}{n:>2}){c['reset']} {r.code}{note}")
                    numbered.append(r)
                    n += 1
                print()

            # ── 步驟 5：選擇結果 ──────────────────────────────────────────
            print(f"{c['bold']}【步驟 5】選擇要輸出的結果{c['reset']}")
            result_idx = _choose("請選擇結果編號：", [r.code[:60] for r in numbered], allow_back=True)
            if result_idx is None:
                # 返回輸入步驟
                break
            chosen = numbered[result_idx]

            # ── 步驟 6：是否輸出混淆結果 ──────────────────────────────────
            print(f"\n{c['bold']}【步驟 6】輸出方式{c['reset']}")
            OUTPUT_OPTS = ["顯示在終端機", "儲存到檔案"]
            out_idx = _choose("請選擇輸出方式：", OUTPUT_OPTS, allow_back=True)
            if out_idx is None:
                continue  # 重新選擇結果

            if out_idx == 0:
                # 顯示在終端機
                print(f"\n{c['bold']}混淆結果：{c['reset']}")
                print(f"  {c['cyan']}{chosen.code}{c['reset']}")
                if chosen.note:
                    print(f"  {c['dim']}備註：{chosen.note}{c['reset']}")
                print()
            else:
                # 儲存到檔案
                print(f"  {c['dim']}(按 Ctrl-C 可返回){c['reset']}")
                try:
                    outpath = input("請輸入輸出檔案路徑：").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    continue
                if not outpath:
                    print("  路徑不可為空。\n")
                    continue
                try:
                    with open(outpath, "a", encoding="utf-8") as fh:
                        fh.write(chosen.code + "\n")
                    print(f"  {c['green']}✓ 已附加寫入：{outpath}{c['reset']}\n")
                except OSError as e:
                    print(f"  寫入失敗：{e}\n")

            # ── 詢問是否繼續 ──────────────────────────────────────────────
            print(f"{c['bold']}繼續操作？{c['reset']}")
            CONTINUE_OPTS = ["重新開始（選擇新平台）", "再次選擇結果（同一指令）", "離開"]
            cont_idx = _choose("請選擇：", CONTINUE_OPTS)
            if cont_idx is None or cont_idx == 2:
                print("感謝使用，再見！")
                return
            elif cont_idx == 0:
                break   # 跳出結果迴圈，回到平台選擇
            # cont_idx == 1：繼續結果選擇迴圈
        # end while True (result loop)
    # end while True (platform loop)


def main(argv=None) -> int:
    args = parse_args(argv)

    if args.output:
        # truncate so each run starts clean
        open(args.output, "w", encoding="utf-8").close()

    if args.interactive:
        _interactive_menu(args)
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
