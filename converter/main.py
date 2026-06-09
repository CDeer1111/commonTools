import argparse
from enums import EncodingType, Delimiter, PrefixStyle, get_valid_prefixes
from converter import UniversalConverter

def run_interactive(conv):
    print("\n" + "="*50)
    print("      🛠  萬用編碼轉換工具 (輸入 'q' 離開)")
    print("="*50)

    while True:
        text = input("\n📝 請輸入原始內容: ")
        if text.lower() == 'q': break

        # 1. 選擇來源
        print(f"📥 來源編碼: {[e.value for e in EncodingType]}")
        f_val = input("   請選擇 [utf-8]: ") or "utf-8"
        f_enc = EncodingType(f_val)

        # 2. 選擇目標
        print(f"📤 目標編碼: {[e.value for e in EncodingType]}")
        t_val = input("   請選擇 [ascii-16]: ") or "ascii-16"
        t_enc = EncodingType(t_val)

        # 3. 選擇前綴 (手動顯示，避免 Python 轉義)
        valid_p = get_valid_prefixes(t_enc)
        # 手動組合顯示字串
        p_display = []
        for p in valid_p:
            if p.value == "":
                p_display.append("none")
            else:
                p_display.append(p.value)  # 直接取 value，不經 list repr

        print(f"🏷️  可用前綴: {', '.join(p_display)}")

        p_val = input(f"   請選擇前綴碼 [none]: ") or ""

        target_p = PrefixStyle.NONE
        for p in valid_p:
            if p.value == p_val:
                target_p = p
                break

        # 4. 選擇分隔
        print(f"🔗 分隔符: {', '.join([d.name.lower() for d in Delimiter])}")
        d_val = input("   請選擇 [space]: ") or "space"
        delim = Delimiter[d_val.upper()]

        try:
            mid = conv.decode_to_codepoints(text, f_enc)
            res = conv.encode_from_codepoints(mid, t_enc, delim, target_p)
            print(f"\n✅ 轉換結果:\n{res}")
        except Exception as e:
            print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("text", nargs="?")
    parser.add_argument("-f", "--from-enc", default="utf-8")
    parser.add_argument("-t", "--to-enc", default="ascii-16")
    parser.add_argument("-d", "--delimiter", default="space")
    parser.add_argument("-p", "--prefix", default="")
    parser.add_argument("-i", "--interactive", action="store_true")

    args = parser.parse_args()
    conv = UniversalConverter()

    if args.interactive or not args.text:
        run_interactive(conv)
    else:
        try:
            f_enc = EncodingType(args.from_enc)
            t_enc = EncodingType(args.to_enc)
            delim = Delimiter[args.delimiter.upper()]
            target_p = PrefixStyle.NONE
            for p in get_valid_prefixes(t_enc):
                if p.value == args.prefix:
                    target_p = p
            mid = conv.decode_to_codepoints(args.text, f_enc)
            print(conv.encode_from_codepoints(mid, t_enc, delim, target_p))
        except Exception as e:
            print(f"Error: {e}")
