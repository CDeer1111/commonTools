你可以使用 `-h` 查看使用說明，及 `-i` 進行互動式操作
```
  python3 main.py Hello -f utf-8 -t ascii-16 -d space -p 0x
  ->  0x48 0x65 0x6C 0x6C 0x6F

  -f, --from-enc FROM_ENC
  -t, --to-enc TO_ENC
  -d, --delimiter DELIMITER
  -p, --prefix PREFIX        #\x 失敗可以嘗試 \\x
  -i, --interactive
```
```
-d 分隔所提供的選擇
  none = ""
  space = " "
  comma = ","
  semicolon = ";"
  newline = "\n"
```
