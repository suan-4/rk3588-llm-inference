#!/usr/bin/env python3
"""用 AST 对比，判定重建源码与真源码在「逻辑」上是否等价（忽略一切格式差异）。"""

import ast
import os

REAL = r"C:\Users\何\Desktop\work\computer\大模型故障检测\backend\app\services\kg_service.py"
REC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "backend", "services", "kg_service.RECOVERED.py")


def funcs(path):
    """提取每个顶层/类内函数的 AST dump。"""
    with open(path, encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = ast.dump(node, annotate_fields=False, include_attributes=False)
        elif isinstance(node, ast.ClassDef):
            out["class:" + node.name] = ast.dump(
                node, annotate_fields=False, include_attributes=False)
    return out


def main():
    a = funcs(REAL)
    b = funcs(REC)

    names = sorted(set(a) | set(b))
    print(f"{'函数/类':<42}{'真源码':>7}{'重建':>7}  结论")
    print("-" * 74)
    same = diff = 0
    for n in names:
        if n not in a:
            print(f"{n:<42}{'—':>7}{'有':>7}  只在重建里有")
            diff += 1
        elif n not in b:
            print(f"{n:<42}{'有':>7}{'—':>7}  只在真源码里有")
            diff += 1
        elif a[n] == b[n]:
            print(f"{n:<42}{'有':>7}{'有':>7}  [一致]")
            same += 1
        else:
            print(f"{n:<42}{'有':>7}{'有':>7}  [有差异]")
            diff += 1
    print()
    print(f"逻辑完全一致: {same} 个    有差异: {diff} 个")


if __name__ == "__main__":
    main()
