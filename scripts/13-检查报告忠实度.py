#!/usr/bin/env python3
"""检查生成的报告对知识库的覆盖程度（用关键片段匹配，避免同义表述误判）。"""

import glob
import os

# 知识库里的条目 -> 报告里可能出现的写法（取核心词）
RISK_KEYS = {
    "蹲底风险": ["蹲底"],
    "冲顶风险": ["冲顶"],
    "轿厢非正常移动": ["非正常移动"],
    "溜车风险": ["溜车"],
}
ACTION_KEYS = {
    "更换制动弹簧": ["更换", "制动弹簧"],
    "停止使用并专项检验": ["专项检验"],
}
SECTION_KEYS = ["故障原因分析", "风险评估", "整改建议", "综合结论"]


def check(path):
    with open(path, encoding="utf-8") as f:
        t = f.read()
    hit_r = sum(1 for k, ws in RISK_KEYS.items() if all(w in t for w in ws))
    hit_a = sum(1 for k, ws in ACTION_KEYS.items() if all(w in t for w in ws))
    hit_s = sum(1 for s in SECTION_KEYS if s in t)
    return len(t), hit_r, hit_a, hit_s


here = os.path.dirname(os.path.abspath(__file__))
files = sorted(glob.glob(os.path.join(here, "..", "report_test_*.txt")))

print(f"{'报告':<18}{'字数':>6}{'风险覆盖':>10}{'建议覆盖':>10}{'章节完整':>10}")
print("-" * 56)
for p in files:
    n, r, a, s = check(p)
    print(f"{os.path.basename(p):<18}{n:>6}{f'{r}/4':>10}{f'{a}/2':>10}{f'{s}/4':>10}")

print()
print("各报告实际提到的风险/建议关键词：")
for p in files:
    with open(p, encoding="utf-8") as f:
        t = f.read()
    rs = [k for k, ws in RISK_KEYS.items() if all(w in t for w in ws)]
    ac = [k for k, ws in ACTION_KEYS.items() if all(w in t for w in ws)]
    print(f"  {os.path.basename(p)}")
    print(f"    风险: {'、'.join(rs) if rs else '（无）'}")
    print(f"    建议: {'、'.join(ac) if ac else '（无）'}")
