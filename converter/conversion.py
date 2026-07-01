import base64
import urllib.parse
from enums import EncodingType, PrefixStyle, Delimiter

class UniversalConverter:
    def __init__(self):
        pass

    def decode_to_codepoints(self, text, from_enc):
        """將任何輸入格式轉為整數碼點列表"""
        if from_enc == EncodingType.UTF8:
            return [ord(c) for c in text]
        
        elif from_enc == EncodingType.BASE64:
            decoded_bytes = base64.b64decode(text)
            return list(decoded_bytes)
            
        elif from_enc == EncodingType.URL:
            decoded_str = urllib.parse.unquote(text)
            return [ord(c) for c in decoded_str]

        # 處理帶有前綴或分隔符的進位制輸入
        clean_text = text.replace(',', ' ').replace(';', ' ')
        for p in ["0x", "0b", "0o", "0d", "\\x", "\\b", "\\0", "\\d"]:
            clean_text = clean_text.replace(p, " ")

        parts = clean_text.split()
        
        try:
            if from_enc == EncodingType.BIN or from_enc == EncodingType.ASCII_8:
                pass
        except:
            pass

        # 二進位相關
        if from_enc in [EncodingType.BIN]:
            return [int(p, 2) for p in parts]

        # 八進位相關
        elif from_enc in [EncodingType.OCT, EncodingType.ASCII_8]:
            return [int(p, 8) for p in parts]

        # 十進位相關
        elif from_enc in [EncodingType.DEC, EncodingType.ASCII_10]:
            return [int(p, 10) for p in parts]

        # 十六進位相關
        elif from_enc in [EncodingType.HEX, EncodingType.ASCII_16]:
            return [int(p, 16) for p in parts]

        raise ValueError(f"不支援的編碼類型: {from_enc.value}")
        
        return []

    def encode_from_codepoints(self, codepoints, to_enc, delimiter, prefix):
        """將碼點列表轉為目標格式字串"""
        if to_enc == EncodingType.UTF8:
            return "".join([chr(c) for c in codepoints])
        
        if to_enc == EncodingType.BASE64:
            bytes_data = bytes(codepoints)
            return base64.b64encode(bytes_data).decode('utf-8')

        if to_enc == EncodingType.URL:
            target_str = "".join([chr(c) for c in codepoints])
            return urllib.parse.quote(target_str)

        # 處理進位制輸出
        formatted_parts = []
        for c in codepoints:
            if to_enc in [EncodingType.BIN]:
                val = format(c, '08b')
            elif to_enc in [EncodingType.OCT, EncodingType.ASCII_8]:
                val = format(c, 'o')  # 八進位不補零
            elif to_enc in [EncodingType.DEC, EncodingType.ASCII_10]:
                val = str(c)
            elif to_enc in [EncodingType.HEX, EncodingType.ASCII_16]:
                val = format(c, '02X')
            else:
                val = ""
            
            # 加上使用者設定的前綴
            formatted_parts.append(f"{prefix.value}{val}")

        # 使用使用者設定的分隔符結合
        return delimiter.value.join(formatted_parts)
