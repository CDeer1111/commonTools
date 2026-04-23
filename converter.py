import argparse
import os

class CustomFormatter(argparse.HelpFormatter):
    def __init__(self, prog):
        super().__init__(prog, max_help_position=40, width=100)

def to_bytes(data, mode):
    """ 輸入統一轉換為 bytes """
    try:
        if mode == "str":
            return data.encode('utf-8')
        elif mode == "ascii10":
            return bytes([int(x) for x in data.split()])
        elif mode == "ascii16":
            val = "".join(data.split()).replace("0x", "")
            return bytes.fromhex(val)
        elif mode == "16":
            val = "".join(data.split()).replace("0x", "")
            return bytes.fromhex(val)
        elif mode == "10":
            val = int(data.strip())
            return val.to_bytes((val.bit_length() + 7) // 8, 'big') or b'\x00'
        elif mode == "8":
            val = int("".join(data.split()), 8)
            return val.to_bytes((val.bit_length() + 7) // 8, 'big') or b'\x00'
        elif mode == "2":
            val = int("".join(data.split()), 2)
            return val.to_bytes((val.bit_length() + 7) // 8, 'big') or b'\x00'
    except Exception as e:
        raise ValueError(f"解析錯誤: {e}")

def format_output(raw_bytes, mode):
    if not raw_bytes and mode != "str": return "0"
    """ bytes 轉換為輸出格式 """
    if mode == "str":
        return raw_bytes.decode('utf-8', errors='replace')
    elif mode == "ascii10":
        return " ".join(str(b) for b in raw_bytes)
    elif mode == "ascii16":
        return raw_bytes.hex(' ', 1)
    elif mode == "16":
        return raw_bytes.hex()
    elif mode == "10":
        return str(int.from_bytes(raw_bytes, 'big'))
    elif mode == "8":
        return oct(int.from_bytes(raw_bytes, 'big'))[2:]
    elif mode == "2":
        if not raw_bytes: return "0"
        return bin(int.from_bytes(raw_bytes, 'big'))[2:]

def main():
    parser = argparse.ArgumentParser(
        description="進制轉換工具",
        formatter_class=CustomFormatter
    )
    
    # 輸入：直接輸入的資料，或是檔案路徑
    group = parser.add_mutually_exclusive_group()
    group.add_argument("data", nargs='?', help="輸入轉換內容")
    group.add_argument("-i", "--input", metavar="INPUT", help="輸入檔案路徑")

    # 格式參數
    choices = ["str", "ascii10", "ascii16", "16", "10", "8", "2"]
    parser.add_argument("-f", "--from", dest="src_mode", choices=choices, 
                        required=True, metavar="{str,ascii10,ascii16,16,10,8,2}", help="輸入的格式")
    parser.add_argument("-t", "--to", dest="dst_mode", choices=choices, 
                        required=True, metavar="{str,ascii10,ascii16,16,10,8,2}", help="輸出的格式")
    
    args = parser.parse_args()
    if not args.data and not args.input:
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
            content = args.data
            
        # 執行轉換
        intermediate_bytes = to_bytes(content, args.src_mode)
        result = format_output(intermediate_bytes, args.dst_mode)
        print(result)

    except Exception as e:
        print(f"錯誤: {e}")

if __name__ == "__main__":
    main()
