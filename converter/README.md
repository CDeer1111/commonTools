你可以使用 `-h` 查看使用說明，及 `-i` 進行互動式操作
# 互動模式
```
python3 main.py -i
```

# 命令列模式
```
  python3 main.py "Hello" -f utf-8 -t ascii-16 -d space -p 0x
  ->  0x48 0x65 0x6C 0x6C 0x6F

python3 main.py [-h] [-f FROM_ENC] [-t TO_ENC] [-d DELIMITER] [-p PREFIX]
               [-i]
               [text]

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
