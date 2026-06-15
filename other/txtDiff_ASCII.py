import sys
file1 = sys.argv[1]
file2 = sys.argv[2]

try:
    with open(file1, 'r', encoding='utf-8') as f1, \
            open(file2, 'r', encoding='utf-8') as f2:
        t1 = f1.read()
        t2 = f2.read()

        txtDiff = ""

        print("總共找到: ", end="")
        for c1, c2 in zip(t1, t2):
            if c1 != c2:
                print(c2, end="")
                diff = ord(c2) - ord(c1)
                txtDiff += chr(diff)

        print("\n相減結果:", txtDiff)

except FileNotFoundError:
    print("Error")
