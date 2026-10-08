#!/usr/bin/env python3
"""从 .pyc 里导出代码结构（函数名、常量、变量名），用于人工恢复源码。

用法（在板子上跑，因为需要 Python 3.10 才能加载 3.10 的 pyc）：
    python3 /userdata/dump_pyc.py /userdata/backend/app/services/kg_service.pyc
"""

import dis
import marshal
import sys
import types


def load_code(path):
    with open(path, "rb") as f:
        f.read(16)  # 跳过 pyc 头部（magic + flags + mtime + size）
        return marshal.load(f)


def walk(code, indent=0, out=None):
    pad = "  " * indent
    nlines = len(list(code.co_lines())) if hasattr(code, "co_lines") else 0
    out.append(f"{pad}=== {code.co_name}  (行数={nlines}) ===")
    out.append(f"{pad}  参数: {code.co_varnames[:code.co_argcount]}")
    out.append(f"{pad}  局部变量: {list(code.co_varnames)}")
    out.append(f"{pad}  闭包变量: {list(code.co_freevars)}")
    out.append(f"{pad}  引用全局: {list(code.co_names)}")

    strs = [c for c in code.co_consts if isinstance(c, str) and len(c) > 20]
    if strs:
        out.append(f"{pad}  长字符串常量 ({len(strs)} 个):")
        for s in strs:
            first = s.strip().splitlines()[0][:70]
            out.append(f"{pad}    - {first}")

    for c in code.co_consts:
        if isinstance(c, types.CodeType):
            out.append("")
            walk(c, indent + 1, out)


def main():
    path = sys.argv[1]
    code = load_code(path)
    out = []
    walk(code, 0, out)
    print("\n".join(out))


if __name__ == "__main__":
    main()
