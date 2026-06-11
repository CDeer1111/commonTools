from enum import Enum

class EncodingType(Enum):
    UTF8 = "utf-8"
    BASE64 = "base64"
    URL = "url"
    BIN = "2"
    OCT = "8"
    DEC = "10"
    HEX = "16"
    ASCII_8 = "ascii-8"
    ASCII_10 = "ascii-10"
    ASCII_16 = "ascii-16"

class Delimiter(Enum):
    NONE = ""
    SPACE = " "
    COMMA = ","
    SEMICOLON = ";"
    NEWLINE = "\n"

class PrefixStyle(Enum):
    NONE = ""
    # 二進位
    B_0b = "0b"
    B_b = r"\b"
    # 八進位
    O_0o = "0o"
    O_0 = r"\0"
    # 十進位
    D_0d = "0d"
    D_d = r"\d"
    # 十六進位
    H_0x = "0x"
    H_x = r"\x"

# 核心邏輯：定義哪些前綴屬於哪個進位制
PREFIX_MAP = {
    EncodingType.BIN: [PrefixStyle.NONE, PrefixStyle.B_0b, PrefixStyle.B_b],
    EncodingType.OCT: [PrefixStyle.NONE, PrefixStyle.O_0o, PrefixStyle.O_0],
    EncodingType.DEC: [PrefixStyle.NONE, PrefixStyle.D_0d, PrefixStyle.D_d],
    EncodingType.HEX: [PrefixStyle.NONE, PrefixStyle.H_0x, PrefixStyle.H_x],
    EncodingType.ASCII_8: [PrefixStyle.NONE, PrefixStyle.O_0o, PrefixStyle.O_0],
    EncodingType.ASCII_10: [PrefixStyle.NONE, PrefixStyle.D_0d, PrefixStyle.D_d],
    EncodingType.ASCII_16: [PrefixStyle.NONE, PrefixStyle.H_0x, PrefixStyle.H_x],
}

def get_valid_prefixes(target: EncodingType):
    """根據目標編碼過濾不合法的前綴"""
    return PREFIX_MAP.get(target, [PrefixStyle.NONE])
