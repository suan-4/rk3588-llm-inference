#!/usr/bin/env python3
"""剥掉类型注解和 docstring 后再比 AST —— 判定重建源码在「运行行为」上是否等价。"""

import ast
import os

REAL = r"C:\Users\何\Desktop\work\computer\大模型故障检测\backend\app\services\kg_service.py"
REC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "backend", "services", "kg_service.RECOVERED.py")


class Strip(ast.NodeTransformer):
    """抹掉参数/返回值注解、docstring、函数装饰器。"""

    def visit_FunctionDef(self, node):
        node.returns = None
        node.decorator_list = []
        node.type_comment = None
        for a in list(node.args.args) + list(node.args.kwonlyargs) + list(node.args.posonlyargs):
            a.annotation = None
        if node.args.vararg:
            node.args.vararg.annotation = None
        if node.args.kwarg:
            node.args.kwarg.annotation = None
        if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            node.body = node.body[1:] or [ast.Pass()]
        self.generic_visit(node)
        return node

    def visit_AnnAssign(self, node):
        # 变量注解赋值 x: int = 1  ->  x = 1
        if node.value is None:
            return ast.Pass()
        return ast.Assign(targets=[node.target], value=node.value)


def dump(path):
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    tree = Strip().visit(tree)
    ast.fix_missing_locations(tree)
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = ast.dump(node, annotate_fields=False, include_attributes=False)
        elif isinstance(node, ast.ClassDef):
            out["class:" + node.name] = ast.dump(
                node, annotate_fields=False, include_attributes=False)
    return out


def main():
    a, b = dump(REAL), dump(REC)
    names = sorted(set(a) | set(b))
    same = diff = 0
    print(f"{'函数/类':<42}{'结论'}")
    print("-" * 60)
    for n in names:
        if n in a and n in b and a[n] == b[n]:
            print(f"{n:<42}[一致]")
            same += 1
        else:
            print(f"{n:<42}[有差异]")
            diff += 1
    print()
    print(f"运行行为等价: {same} 个    仍有差异: {diff} 个")


if __name__ == "__main__":
    main()
