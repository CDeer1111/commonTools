操作方式
```
python3 obfuscator_all_zh.py -p bash "cat /etc/hosts"
python3 obfuscator_all_zh.py -f test.py
```

```
python3 obfuscator_all_zh.py [-h] [-p {bash,cmd,python,auto}] [-i] [-f FILE] \
                             [--whole] [-o OUTPUT] [--only {alias,split,encode}] [--max MAX_N] [--json] \
                             [--no-color] [command]

positional arguments:
  command                                       要混淆的指令（省略則從標準輸入讀取，或使用 -f / -i）

options:
  -h, --help                                    show this help message and exit
  -p, --platform {bash,cmd,python,auto}         目標平台（預設：auto）
  -i, --interactive                             進入互動式選單界面
  -f, --file FILE                               從檔案讀取指令或程式碼並進行混淆
  --whole                                       將檔案內容視為單一整體處理（Python 或 .py 檔案時自動啟用）
  -o, --output OUTPUT                           將結果寫入指定檔案而非標準輸出
  --only {alias,split,encode}                   只顯示特定類別的混淆結果
  --max MAX_N                                   每個類別最多顯示幾種變體（預設：5）
  --json                                        以 JSON 格式輸出（便於程式讀取）
  --no-color                                    停用 ANSI 色彩輸出

```

使用互動式界面
```
python3 obfuscator_all_zh.py -i    # 可直接使用
python3 obfuscator_all_en.py -i    # 可直接使用

python3 obfuscator.py -i           # 使用必須下載 obfuscatorData 資料夾
```
