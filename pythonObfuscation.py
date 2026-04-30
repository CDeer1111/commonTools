import sys
import keyword
import builtins
import argparse
import re

class CustomFormatter(argparse.HelpFormatter):
    def __init__(self, prog):
        super().__init__(prog, max_help_position=40, width=80)

def to_chr(text):
    """轉換為 chr(x) + chr(y) 格式"""
    return " + ".join([f"chr({ord(c)})" for c in text])

def to_hex(text):
    """轉換為 \x00 16進位字串格式"""
    return "".join([f"\\x{ord(c):02x}" for c in text])

def to_oct(text):
    """轉換為 \000 8進位字串格式"""
    return "".join([f"\\{oct(ord(c))[2:]:0>3}" for c in text])

def print_encoded_formats(target_key, args_str=""):
    """統一輸出四種編碼格式"""
    print(f"    [1. 明文字串]:")
    print(f"    __builtins__.__dict__['{target_key}']{args_str}\n")

    print(f"    [2. Hex 16進位編碼]:")
    print(f"    __builtins__.__dict__['{to_hex(target_key)}']{args_str}\n")

    print(f"    [3. Octal 8進位編碼]:")
    print(f"    __builtins__.__dict__['{to_oct(target_key)}']{args_str}\n")

    print(f"    [4. chr() 動態拼接]:")
    print(f"    __builtins__.__dict__[{to_chr(target_key)}]{args_str}\n")

def analyze(text):
    text = text.strip()

    # --- 1. 意圖分析正則匹配 ---
    import_match = re.match(r'^import\s+([\w\.]+)$', text)
    call_match = re.match(r'^([a-zA-Z_]\w*)\((.*)\)$', text)
    is_single_word = " " not in text and "(" not in text

    print(f"\n[*] 分析目標: {text}")
    print("=" * 60)

    target_key = ""  # 要去字典裡抓取的目標 (如 'exec', '__import__')
    args_str = ""    # 後面跟著的參數 (如 "('os')", "(input())")

    # --- 2. 意圖判斷與策略制定 ---
    if import_match:
        module_name = import_match.group(1)
        print(f"[*] 意圖偵測：【模組匯入】")
        print(f"    [💡 策略]: 提取模組 '{module_name}'，使用 __import__ 加載")
        target_key = "__import__"
        args_str = f"('{module_name}')"

    elif call_match:
        func_name = call_match.group(1)
        args = call_match.group(2)
        danger_zone = ['eval', 'exec', 'open', 'input', 'getattr']
        if func_name in danger_zone:
            print(f"[*] 意圖偵測：【🔥 高權限指令執行】")
        else:
            print(f"[*] 意圖偵測：【一般函數呼叫】")

        print(f"    [💡 策略]: 隱藏函數 '{func_name}'，參數保留")
        target_key = func_name
        args_str = f"({args})"

    elif is_single_word:
        if text in dir(builtins):
            print(f"[*] 意圖偵測：【內建函數/屬性】")
            print(f"    [💡 策略]: 直接編碼隱藏函數名稱")
            target_key = text
            args_str = ""
        elif keyword.iskeyword(text):
            print(f"[*] 意圖偵測：【系統關鍵字】")
            print(f"    [💡 策略]: 關鍵字無法直接字典化，使用 exec() 封裝執行")
            target_key = "exec"
            args_str = f"({repr(text)})" # 使用 repr 避免引號衝突
        else:
            print(f"[*] 意圖偵測：【普通字串/潛在模組】")
            print(f"    [💡 策略]: 假設為外部模組，嘗試使用 __import__ 加載")
            target_key = "__import__"
            args_str = f"('{text}')"

    else:
        print(f"[*] 意圖偵測：【一般代碼區塊】")
        print(f"    [💡 策略]: 複雜指令無法直接呼叫，使用 exec() 封裝整段代碼")
        target_key = "exec"
        args_str = f"({repr(text)})"

    # --- 3. 輸出所有編碼格式 ---
    print("-" * 60)
    print("[+] 所有可讀取的字典混淆格式:\n")
    print_encoded_formats(target_key, args_str)

    # --- 4. 深度混淆加碼 (針對 input 相關) ---
    if args_str == "(input())":
        print("-" * 60)
        print(f"    [🔥 深度組合: 連同 input() 內部一起混淆 (Hex 為例)]:")
        hex_func = to_hex(target_key)
        input_hex = to_hex("input")
        print(f"    __builtins__.__dict__['{hex_func}'](__builtins__.__dict__['{input_hex}']())\n")

    print("=" * 60 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description="Python 意圖識別與多重字典混淆工具",
        formatter_class=CustomFormatter
    )
    parser.add_argument("text", help="輸入指令 (例: exec(input()), import os, print('x'))")
    args = parser.parse_args()
    analyze(args.text)

if __name__ == "__main__":
    main()
