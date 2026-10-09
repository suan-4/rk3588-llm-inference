#!/usr/bin/env python3
"""把指写函数的真源码和重建源码并排打出来，人工核对差异性质。"""

import ast
import os
import sys

REAL = r"C:\Users\何\Desktop\work\computer\大模型故障检测\backend\app\services\kg_service.py"
REC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "backend", "services", "kg_service.RECOVERED.py")


def get_fn(path, name):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(src, node)
    return None


def main():
    names = sys.argv[1:] or ["_add_coupled"]
    for n in names:
        print("=" * 70)
        print(f"### {n}")
        print("=" * 70)
        print("--- 真源码 ---")
        print(get_fn(REAL, n))
        print("--- 重建 ---")
        print(get_fn(REC, n))
        print()


if __name__ == "__main__":
    main()
