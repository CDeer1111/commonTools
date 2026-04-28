import sys
import keyword
import builtins
import argparse

builtinsList = dir(builtins)
is_keyword = False
is_builtin = False

class CustomFormatter(argparse.HelpFormatter):
    def __init__(self, prog):
        super().__init__(prog, max_help_position=40, width=80)

def find_interchangeable(searchText):
    is_keyword = keyword.iskeyword(searchText)
    is_builtin = searchText in builtinsList

    # 生成混淆組件
    obf_searchText = " + ".join([f"chr({ord(c)})" for c in searchText])
    obf_import = " + ".join([f"chr({ord(c)})" for c in "__import__"])

    dict_chr_access = f"__builtins__.__dict__[{obf_searchText}]"

    print(f"\n[*] 分析目標: {searchText}")
    print("=" * 60)

    # 邏輯判斷與觸發提示
    if is_keyword:
        print(f"[!] 警告: '{searchText}' 是 Python 關鍵字")
        print(f"    需配合 exec() 執行混淆後代碼")

    elif is_builtin:
        print(f"[!] 警告: '{searchText}' 是內建函數/屬性")

        # --- 高權限函數替換邏輯 ---
        danger_zone = ["eval", "exec", "open", "input", "getattr", "__import__", "setattr", "breakpoint"]
        if searchText in danger_zone:
            print(f"    [！危險！] 偵測到高權限函數")
            print(f"    [替換建議]: 隱藏函數名稱以繞過偵測")
            print(f"    原本意思: {searchText}(...)")
            print(f"    替換代碼: __builtins__.__dict__ [{obf_searchText}](...)")

    else:
        # 非內建函數，觸發模組加載提示
        print(f"[*] 提示: '{searchText}' 可能是外部模組")
        print(f"    [轉換提示]: 透過底層字典動態加載模組")
        print(f"    原本意思: __builtins__.__dict__['__import__']('{searchText}')")
        print(f"    混淆代碼: __builtins__.__dict__ [{obf_import}]({obf_searchText})")

    print("-" * 60)
    print(f"[+] 單獨字串混淆 (chr):")
    print(f"    {obf_searchText}")
    print(f"\n[+] 底層字典存取範例:")
    print(f"    {dict_chr_access}")
    print("=" * 60 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description="Python 混淆字典分析工具",
        formatter_class=CustomFormatter
    )
    parser.add_argument("searchText", help="分析的關鍵字、函數或模組名稱")
    args = parser.parse_args()
    find_interchangeable(args.searchText)

if __name__ == "__main__":
    main()
