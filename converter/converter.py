import base64
import urllib.parse
from enums import EncodingType, PrefixStyle, Delimiter

class UniversalConverter:
    def __init__(self):
        pass

    def decode_to_codepoints(self, text, from_enc):
        """將任何輸入格式轉為整數碼點列表"""
        if from_enc in [EncodingType.UTF8, EncodingType.ASCII]:
            return [ord(c) for c in text]
        
        elif from_enc == EncodingType.BASE64:
            decoded_bytes = base64.b64decode(text)
            return list(decoded_bytes)
            
        elif from_enc == EncodingType.URL:
            decoded_str = urllib.parse.unquote(text)
            return [ord(c) for c in decoded_str]

        # 處理帶有前綴或分隔符的進位制輸入
        # 先清理常見分隔符，轉為純字串列表
        clean_text = text.replace(',', ' ').replace(';', ' ')
        # 針對使用者可能輸入的 \x, \b 等進行清理
        for p in ["0x", "0b", "0o", "0d", "\\x", "\\b", "\\0", "\\d"]:
            clean_text = clean_text.replace(p, " ")

        parts = clean_text.split()
        
        try:
            if from_enc == EncodingType.BIN: return [int(p, 2) for p in parts]
            if from_enc == EncodingType.OCT: return [int(p, 8) for p in parts]
            if from_enc == EncodingType.DEC: return [int(p, 10) for p in parts]
            if from_enc == EncodingType.HEX: return [int(p, 16) for p in parts]
        except ValueError:
            raise ValueError(f"輸入內容與來源編碼 {from_enc.value} 不符")
        
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
            if to_enc == EncodingType.BIN: val = format(c, '08b')
            elif to_enc == EncodingType.OCT: val = format(c, 'o')
            elif to_enc == EncodingType.DEC: val = str(c)
            elif to_enc == EncodingType.HEX: val = format(c, '02X')
            else: val = ""
            
            # 加上使用者設定的前綴 (例如 0x)
            formatted_parts.append(f"{prefix.value}{val}")

        # 使用使用者設定的分隔符結合 (預設為空格)
        return delimiter.value.join(formatted_parts)
