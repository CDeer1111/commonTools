"""obfuscatorData — offline command obfuscator engines and data.

零依賴、純離線。將指令混淆所需的型別、共用函式、各平台等價資料/引擎
以及 CLI 邏輯拆分為獨立模組，供 obfuscator.py 主程式呼叫。
"""
from .data_types import CATEGORIES, Engine, ObfResult
from .data_bash import BASH_EQUIVALENTS, BashAliasEngine, BashEncodeEngine, BashSplitEngine
from .data_windows import CMD_EQUIVALENTS, CmdAliasEngine, CmdEncodeEngine, CmdSplitEngine
from .data_python import PYTHON_EQUIVALENTS, PythonAliasEngine, PythonEncodeEngine, PythonSplitEngine
from .cli import (
    ANSI,
    CATEGORY_TITLE,
    ENGINES,
    auto_platform,
    main,
    parse_args,
    process_once,
    render_text,
    run,
)

__all__ = [
    "CATEGORIES",
    "Engine",
    "ObfResult",
    "BASH_EQUIVALENTS",
    "BashAliasEngine",
    "BashSplitEngine",
    "BashEncodeEngine",
    "CMD_EQUIVALENTS",
    "CmdAliasEngine",
    "CmdSplitEngine",
    "CmdEncodeEngine",
    "PYTHON_EQUIVALENTS",
    "PythonAliasEngine",
    "PythonSplitEngine",
    "PythonEncodeEngine",
    "ENGINES",
    "CATEGORY_TITLE",
    "ANSI",
    "auto_platform",
    "run",
    "render_text",
    "parse_args",
    "process_once",
    "main",
]
