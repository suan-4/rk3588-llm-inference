#!/usr/bin/env python3
"""模拟知识库变大：往 prompt 里注入不同数量的图谱内容，测 prefill / decode 变化。

原理：Neo4j 变大只会通过「查询结果变多 → prompt 变长」影响推理速度。
      所以直接构造不同长度的、格式和真实图谱输出一致的 prompt。

用法（先做好端口转发 adb forward tcp:18080 tcp:8080）：
    python scripts/11-测试上下文长度影响.py

真实数据以 rkllm 日志为准：
    adb shell "grep -A3 Prefill /userdata/rkllm/bench.log"
"""

import json
import sys
import time
import urllib.request

API = "http://127.0.0.1:18080/rkllm_chat"

# 一行真实的图谱输出（和后端 _build_prompt 拼出来的格式一致）
LINE = "制动器：制动力下降(性能退化)；现象：制停距离延长；风险：轿厢非正常移动、溜车风险；建议：更换制动衬垫"

HEAD = "[严格指令] 你是报告生成器。下面是从知识库检索到的故障信息，请用一句话概括最严重的风险，不要列点。\n\n"

# 每一档的行数（一行约 38 个 token）
LEVELS = [1, 5, 13, 26, 52]


def ask(prompt, timeout=600):
    body = json.dumps(
        {"messages": [{"role": "user", "content": prompt}],
         "stream": False, "enable_thinking": False},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        API, data=body, headers={"Content-Type": "application/json; charset=utf-8"}
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return time.time() - t0, data


def main():
    print(f"{'行数':>5} {'估算输入token':>14} {'端到端(秒)':>12}  回答前20字")
    print("-" * 70)

    for n in LEVELS:
        content = "\n".join([LINE] * n)
        prompt = HEAD + content
        try:
            dt, data = ask(prompt)
            text = ""
            ch = data.get("choices", [])
            if ch:
                text = (ch[-1].get("message", {}) or {}).get("content", "") or ""
            text = text.replace("\n", " ")[:20]
            print(f"{n:>5} {n * 38:>14} {dt:>12.1f}  {text}")
        except Exception as e:
            print(f"{n:>5} {n * 38:>14}        失败: {e}")
        sys.stdout.flush()
        time.sleep(2)

    print()
    print("完成。真实 token 数请看 rkllm 日志：")
    print('  adb shell "grep -A3 Prefill /userdata/rkllm/bench.log"')


if __name__ == "__main__":
    main()
