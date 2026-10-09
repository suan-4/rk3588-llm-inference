#!/usr/bin/env python3
"""把从字节码反汇编重建的 kg_service.py 与真源码逐行对比，验证重建准确度。"""

import difflib
import os

REAL = r"C:\Users\何\Desktop\work\computer\大模型故障检测\backend\app\services\kg_service.py"
REC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "backend", "services", "kg_service.RECOVERED.py")


def norm(path):
    """去掉空行和纯注释行，忽略行尾空白——只比较有意义的代码。"""
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    out = []
    for ln in lines:
        s = ln.rstrip()
        if not s.strip():
            continue
        if s.strip().startswith("#"):
            continue
        out.append(s)
    return out


def main():
    a = norm(REAL)
    b = norm(REC)
    print(f"真源码有效行: {len(a)}")
    print(f"重建有效行:   {len(b)}")

    sm = difflib.SequenceMatcher(None, a, b)
    print(f"相似度: {sm.ratio() * 100:.1f}%")

    diff = [d for d in difflib.unified_diff(a, b, "REAL", "REC", lineterm="", n=0)
            if d[:1] in "+-" and d[:3] not in ("+++", "---")]
    print(f"差异行数: {len(diff)}")
    print()
    print("=== 差异明细（最多 40 行）===")
    for d in diff[:40]:
        print(d[:160])


if __name__ == "__main__":
    main()
