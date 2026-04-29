import argparse
import os
import re

class CustomFormatter(argparse.HelpFormatter):
    def __init__(self, prog):
        super().__init__(prog, max_help_position=40, width=100)

def autoSplit(inputData, splitSize):
    inputData = inputData.replace("0x", " ").replace("0X", " ").replace("0o", " ").replace("0b", " ")
    inputData = inputData.strip()
    if not inputData: return []

    if " " in inputData:
        return [n.zfill(splitSize) for n in inputData.split()]
    else:
        nfill = len(inputData) % splitSize
        if nfill > 0:
            inputData = inputData.zfill(len(inputData) + (splitSize - nfill))
        return re.findall(f".{{1,{splitSize}}}", inputData)

def conversionBytes(inputData, mode):
    """ 輸入統一轉換為 bytes """
    try:
        if mode in ["ascii10", "ascii16", "16", "8", "2"]:
            inputData = inputData.replace(",", " ")

        if mode == "str":
            return inputData.encode('utf-8')
        if mode == "ascii10":
            inputVal = autoSplit(inputData, 3)
            return bytes([int(n, 10) for n in inputVal])
        elif mode in ["ascii16", "16"]:
            inputVal = autoSplit(inputData, 2)
            return bytes([int(n, 16) for n in inputVal])
        elif mode == "10":
            inputVal = int(inputData.strip())
            return inputVal.to_bytes((inputVal.bit_length() + 7) // 8, 'big') or b'\x00'
        elif mode == "8":
            inputVal = autoSplit(inputData, 3)
            return bytes([int(n, 8) for n in inputVal])
        elif mode == "2":
            inputVal = autoSplit(inputData, 8)
            return bytes([int(n, 2) for n in inputVal])
    except Exception as e:
        raise ValueError(f"解析錯誤: {e}")

def conversionOutput(inputBytes, mode):
    if not inputBytes and mode != "str": return "0"
    """ bytes 轉換為輸出格式 """
    if mode == "str":
        return inputBytes.decode('utf-8', errors='replace')
    elif mode == "ascii10":
        return " ".join(f"{byte:03d}" for byte in inputBytes)
    elif mode == "ascii16":
        return " ".join(f"{byte:02x}" for byte in inputBytes)
    elif mode == "16":
        return inputBytes.hex()
    elif mode == "10":
        return str(int.from_bytes(inputBytes, 'big'))
    elif mode == "8":
        return " ".join(f"{byte:03o}" for byte in inputBytes)
    elif mode == "2":
        return " ".join(f"{byte:08b}" for byte in inputBytes)

def main():
    parser = argparse.ArgumentParser(
        description="進制轉換工具",
        formatter_class=CustomFormatter
    )
    
    # 輸入：直接輸入的資料，或是檔案路徑
    group = parser.add_mutually_exclusive_group()
    group.add_argument("inputData", nargs='?', help="輸入轉換內容")
    group.add_argument("-i", "--input", metavar="INPUT", help="輸入檔案路徑")

    # 格式參數
    choices = ["str", "ascii10", "ascii16", "16", "10", "8", "2"]
    parser.add_argument("-f", "--from", dest="src_mode", choices=choices, 
                        required=True, metavar="{str,ascii10,ascii16,16,10,8,2}", help="輸入的格式")
    parser.add_argument("-t", "--to", dest="dst_mode", choices=choices, 
                        required=True, metavar="{str,ascii10,ascii16,16,10,8,2}", help="輸出的格式")
    
    args = parser.parse_args()
    if not args.inputData and not args.input:
        parser.print_help()
        return
    try:
        if args.input:
            if not os.path.exists(args.input):
                print(f"錯誤: 找不到檔案 '{args.input}'")
                return
            with open(args.input, 'r', encoding='utf-8') as f:
                content = f.read().strip()
        else:
            content = args.inputData
            
        # 執行轉換
        inputBytes = conversionBytes(content, args.src_mode)
        print(inputBytes)
        output = conversionOutput(inputBytes, args.dst_mode)
        print(output)

    except Exception as e:
        print(f"錯誤: {e}")

if __name__ == "__main__":
    main()
