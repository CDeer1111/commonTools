import sys

def solve():
    file1 = sys.argv[1]
    file2 = sys.argv[2]

    try:
        with open(file1, 'r', encoding='utf-8') as f1, \
             open(file2, 'r', encoding='utf-8') as f2:
            t1 = f1.read()
            t2 = f2.read()

            txtDiff = ""
            
            print("Found: ", end="")
            for c1, c2 in zip(t1, t2):
                if c1 != c2:
                    print(c2, end="")
                    # 計算 ASCII 差值
                    diff = ord(c2) - ord(c1)
                    txtDiff += chr(diff)
            
            print("\nResult:", txtDiff)
            
    except FileNotFoundError:
        print("錯誤：找不到指定的檔案。")

if __name__ == "__main__":
    solve()
