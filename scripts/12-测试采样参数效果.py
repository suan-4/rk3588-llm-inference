#!/usr/bin/env python3
"""测 top_k / temperature 改动效果：输出有没有变化？有没有脱离知识库？

做法：
  1. 先调 generate_with_llm=false 拿到知识库的"标准答案"（风险/建议名单）
  2. 再连调 3 次带 LLM 的报告，检查每次报告里覆盖了多少标准答案
  3. 对比 3 次报告的差异，判断随机性是否合适

用法（先做好端口转发 18081 -> 8081）：
    python scripts/12-测试采样参数效果.py
"""

import json
import time
import urllib.request

API = "http://127.0.0.1:18081/api/report/generate"
BODY = {
    "inspection_item_ids": ["INS_BRAKE_001"],
    "abnormal_states": ["STATE_BRAKE_002"],
    "generate_with_llm": False,
}


def post(body, timeout=600):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API, data=data, headers={"Content-Type": "application/json; charset=utf-8"}
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        out = json.loads(resp.read().decode("utf-8"))
    return time.time() - t0, out


def main():
    # 1) 知识库标准答案
    _, base = post(dict(BODY))
    kg = base.get("fault_chain", {})
    risks = [r.get("name") for r in kg.get("all_risks", []) if r.get("name")]
    actions = [a.get("name") for a in kg.get("all_actions", []) if a.get("name")]
    print("知识库标准答案：")
    print(f"  风险 {len(risks)} 项: " + " / ".join(risks))
    print(f"  建议 {len(actions)} 项: " + " / ".join(actions))
    print()

    # 2) 连调 3 次
    reports = []
    print(f"{'次数':>4} {'耗时(秒)':>9} {'字数':>6} {'命中风险':>8} {'命中建议':>8} {'编造嫌疑':>8}")
    print("-" * 62)
    for i in range(1, 4):
        dt, out = post({**BODY, "generate_with_llm": True})
        rep = out.get("report", {})
        text = rep.get("raw_text") or (rep if isinstance(rep, str) else "")
        reports.append(text)

        hit_r = sum(1 for r in risks if r in text)
        hit_a = sum(1 for a in actions if a in text)

        # 粗查编造：报告里出现"风险"/"建议"段但只有很少来自知识库
        fake = len(risks) - hit_r
        print(f"{i:>4} {dt:>9.1f} {len(text):>6} {hit_r}/{len(risks):>6} {hit_a}/{len(actions):>6} {fake:>8}")

    # 3) 三次之间的差异
    print()
    same12 = reports[0] == reports[1]
    same23 = reports[1] == reports[2]
    print(f"第1次和第2次完全相同: {same12}")
    print(f"第2次和第3次完全相同: {same23}")

    with open("report_test_1.txt", "w", encoding="utf-8") as f:
        f.write(reports[0])
    with open("report_test_2.txt", "w", encoding="utf-8") as f:
        f.write(reports[1])
    with open("report_test_3.txt", "w", encoding="utf-8") as f:
        f.write(reports[2])
    print("\n三次报告已存到 report_test_1/2/3.txt")


if __name__ == "__main__":
    main()
