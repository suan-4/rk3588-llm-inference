#!/usr/bin/env python3
"""把 .pyc 完整反汇编输出，用于人工恢复源码。

用法：
    python3 /userdata/dis_pyc.py <pyc路径> <要输出的函数名，可多个；不传则全部>
"""

import dis
import marshal
import sys
import types


def load_code(path):
    with open(path, "rb") as f:
        f.read(16)
        return marshal.load(f)


def collect(code, prefix="", out=None):
    if out is None:
        out = {}
    name = f"{prefix}.{code.co_name}" if prefix else code.co_name
    out[name] = code
    for c in code.co_consts:
        if isinstance(c, types.CodeType):
            collect(c, name, out)
    return out


def main():
    path = sys.argv[1]
    wanted = sys.argv[2:]
    table = collect(load_code(path))

    if not wanted:
        print("可用函数：")
        for k in table:
            print("  " + k)
        return

    for w in wanted:
        match = [k for k in table if k.endswith(w)]
        if not match:
            print(f"=== 没找到 {w} ===")
            continue
        code = table[match[-1]]
        print(f"\n{'=' * 70}")
        print(f"=== {match[-1]} ===")
        print(f"{'=' * 70}")
        dis.dis(code)


if __name__ == "__main__":
    main()
