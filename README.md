# RK3588 端侧大模型推理：部署、性能测量与优化

在瑞芯微 RK3588 开发板上部署 Qwen3-4B 大模型，**实测性能瓶颈、量化优化效果、并给出扩展性预警**。

**测量 → 定位瓶颈 → 优化 → 验证 → 预警**。

---

## 核心成果

| 项目 | 结果 |
|---|---|
| 报告生成端到端耗时 | **114.9 秒 → 29.4 秒（-74%）** |
| Decode 速度 | 5.0 tok/s（实测内存带宽 **23.7 GB/s**，达理论值 95%） |
| 瓶颈定位 | decode 受内存带宽限制，NPU 算力仅用 0.1% |
| 知识库扩展性预警 | prompt 涨到 1000 token 时，prefill 从 0.9 s 暴涨到 **16.7 s** |
| 采样参数修复 | 发现 `top_k=1` 导致 `temperature`/`top_p` 全部失效 |

---

## 一、硬件与软件环境

| 项目 | 配置 |
|---|---|
| 开发板 | 正点原子 ATK-DLRK3588（RK3588，16 GB LPDDR） |
| 系统 | Buildroot，Linux 5.10.209 aarch64 |
| NPU | 3 核，6 TOPS（INT8） |
| 推理框架 | RKLLM Runtime 1.2.3 |
| NPU 驱动 | 0.9.6（官方要求 0.9.7+，启动有警告） |
| 模型 | Qwen3-4B-Instruct-2507，W8A8 量化，4.85 GB |
| 应用 | 电梯故障诊断报告生成系统（Neo4j 知识图谱 + RAG + LLM） |

---

## 二、系统架构

```
Chromium 大屏 (kiosk)
   └→ FastAPI 后端  :8081
        ├→ Neo4j 知识图谱 :7687    (7 类节点 / 8 类关系)
        └→ RKLLM 推理服务 :8080    → Qwen3-4B → NPU
```

知识图谱的数据模型：

```
:Component 部件        (Component)-[:HAS_STATE]->(State)
:State 状态            (State)-[:EVOLVES_TO]->(State)          故障演化
:InspectionItem 检测项  (State)-[:MANIFESTS_AS]->(FaultPhenomenon)
:FaultPhenomenon 现象   (FaultPhenomenon)-[:LEADS_TO]->(RiskEvent)
:RiskEvent 风险         (State)-[:MITIGATED_BY]->(CorrectiveAction)
:CorrectiveAction 措施  (State)-[:COUPLES_WITH]->(State)       故障耦合
:StandardClause 标准条款 (State)-[:DETECTED_BY]->(InspectionItem)
```

---

## 三、实验一：性能基线测量

**目的**：搞清楚推理服务到底能跑多快，瓶颈在哪。

**方法**：在推理服务上打开 `RKLLM_LOG_LEVEL=1`，由 RKLLM runtime 自己输出
prefill / decode 的分阶段统计，避免手工计时误差。

**结果**：

| 场景 | Prefill | Decode | 峰值内存 |
|---|---|---|---|
| 短输入（13 token） | 297.94 ms / 43.63 tok/s | 14014.78 ms / **5.07 tok/s** | 4.56 GB |
| 极短输入（14 token） | 294.22 ms / 47.58 tok/s | 198.02 ms / **5.05 tok/s** | 4.56 GB |
| 长输入（475 token） | 5145.21 ms / 92.32 tok/s | 5344.68 ms / **4.86 tok/s** | 4.57 GB |

**结论**：

1. **Decode 速度锁死在 ~5 tok/s，与输入长度无关** → 这是 memory-bound 的典型特征。
2. **Prefill 越长越高效**（43 → 92 tok/s）→ compute-bound，长输入能填满 NPU。
3. 模型加载时间 4096.65 ms，只在服务启动时发生一次。

### 带宽验证

```
每 token 要读的数据量 = 模型权重大小 = 4.85 GB
每 token 耗时         = 204.6 ms（RKLLM 日志实测）
实测带宽 = 4.85 GB ÷ 0.2046 s = 23.7 GB/s

理论带宽 = 位宽(8字节) × 数据率(1560 MHz × 2) = 25 GB/s
效率 = 23.7 ÷ 25 = 95%    ← 纯顺序读的合理效率
```

**这证明了 decode 已经跑满内存带宽，优化空间只能来自"减少要搬的数据量"（更小的模型 / 更狠的量化）。**

---

## 四、实验二：提示词长度优化

**目的**：报告生成要 114.9 秒，太慢，想缩短。

**方法**：
1. 从 rkllm 日志读出真实 prompt 的组成（发现是 223 token）
2. 分析发现瓶颈 100% 在 decode（写报告），而非 prefill
3. 在系统提示词里加**各段字数上限**，并在 prompt 里明确"禁止重复罗列"

**结果**：

| 指标 | 优化前 | 优化后 | 变化 |
|---|---|---|---|
| Generate token 数 | 552 | 149 | **-73%** |
| 生成耗时 | 112.4 s | 29.9 s | **-73%** |
| 端到端 | 114.9 s | 32.8 s | **-71%** |
| 报告字数 | 2406 | 674 | -72% |
| 出字速度 | 4.91 tok/s | 4.98 tok/s | 不变（硬件上限） |

**结论**：

> **出字速度是硬件上限，改不动。唯一能优化的是「生成多少 token」。**
> 在 5 tok/s 的约束下：`耗时(秒) ≈ 输出 token 数 ÷ 5`
> 所以提示词的长度约束**直接等于时间**。这一刀砍掉 73% 的时间，成本是零。

---

## 五、实验三：知识库规模对推理速度的影响

**目的**：知识图谱会持续变大，需要知道"变大之后会不会拖慢推理"。

**方法**：往 prompt 里注入不同数量的、**格式与真实图谱输出完全一致**的内容，
绕开数据库，只测"输入变长 → 速度怎么变"。

**结果**：

| 注入行数 | Prefill token | **Prefill 耗时** | Prefill 速度 | **Decode 速度** | 端到端 |
|---|---|---|---|---|---|
| 1 | 76 | 0.92 s | 82.98 tok/s | 5.12 tok/s | 5.2 s |
| 5 | 157 | 1.73 s | 90.81 tok/s | 5.03 tok/s | 5.6 s |
| 13 | 309 | 3.61 s | 85.68 tok/s | 4.86 tok/s | 8.6 s |
| 26 | 499 | 6.65 s | 74.99 tok/s | 4.71 tok/s | 12.2 s |
| 52 | 993 | **16.71 s** | 59.41 tok/s | 4.33 tok/s | 23.0 s |

**结论**：

1. **Prefill 超线性增长**：输入涨 13 倍，耗时涨 18 倍，拟合约 `token^1.3`
   （attention 复杂度 O(n²)）。**外推 2000 token 约需 41 秒**。
2. **Decode 只降 15%**：KV cache 在 993 token 时仅 143 MB，占权重总量 2.9%。
   且受 `max_context_limit=4096` 约束，**降幅上限约 20%**。
3. **风险全在 prefill**：知识库涨 4 倍 → prompt ~1000 token → 用户要**干等 16.7 秒**。

**防护措施**（已写入文档）：查询层加 `WHERE severity >= 3` / `LIMIT`；
拼 prompt 时按严重度取 top-N；加 prompt 长度监控告警。

---

## 六、实验四：采样参数与输出忠实度

**目的**：模型输出每次都一模一样（缺乏变化），但又不能放开到编造内容。

**发现**：`flask_server.py` 里 `top_k = 1` —— 这是**贪心解码**，
导致 `temperature=0.8`、`top_p=0.9` **全部失效**（是死参数）。

**方法**：改为 `top_k=20` / `temperature=0.6`，并在提示词中加入**事实约束**：

```
【事实约束】只能使用下方提供的故障信息。禁止编造、推测或补充其中未出现的
部件名称、故障现象、风险项和整改措施。若某项信息缺失，就略过不写。
```

**结果**（连续 3 次）：

| 报告 | 字数 | 风险覆盖 | 建议覆盖 | 章节完整 | 耗时 |
|---|---|---|---|---|---|
| 1 | 223 | **4/4** | **2/2** | **4/4** | 31.6 s |
| 2 | 211 | **4/4** | **2/2** | **4/4** | 28.2 s |
| 3 | 241 | **4/4** | **2/2** | **4/4** | 29.6 s |

**结论**：

1. 三次输出**内容各不相同**（随机性恢复），但每次都 **100% 覆盖知识库内容**。
2. **采样参数管"有无变化"，提示词管"事实性"** —— 两者分工完全不同。
   想保证不编造，靠的是提示词约束，不是把 temperature 调到 0。

---

## 七、关键结论汇总

### 端侧推理的三个硬约束

| 约束 | 数值 | 能不能改 |
|---|---|---|
| **内存带宽** | 25 GB/s（实测 23.7，效率 95%） | ❌ 焊死在板子上 |
| **Decode 速度** | 带宽 ÷ 模型大小 = 4.85 GB → 5 tok/s | ⚠️ 只能靠换模型/量化 |
| **Prefill 复杂度** | O(n²)，实测 ∝ n^1.3 | ✅ **控制输入长度** |

### Prefill vs Decode 的本质差别

| | Prefill | Decode |
|---|---|---|
| 一次处理几个位置 | n 个（并行） | 1 个（串行） |
| 注意力复杂度 | O(n²) | O(n) |
| 瓶颈 | 算力（compute-bound） | 内存带宽（memory-bound） |
| 姿态 | NPU 满载 | NPU 99% 时间在等数据 |
| 速度 | 96 tok/s | 5 tok/s |
| 优化方向 | **控制输入长度** | 换小模型 / 量化 |

### 为什么"必须读全部权重"

```
输出向量(2560维) = 权重矩阵 W(4.85 GB) × 输入向量 x(2560维)
```

矩阵乘法的定义决定：**要算出输出，W 的每一个元素都必须参与运算**。
NPU 片上缓存只有几 MB，装不下 4.85 GB，所以每生成一个 token
都要把全部权重从 DRAM 搬进芯片一遍。

```
搬运总量 = 4.85 GB × 输出 token 数
```

---

## 八、目录结构

```
.
├── README.md                              本文件
├── docs/
│   ├── 01-环境与部署清单.md                环境准备、装系统、部署流程
│   ├── 02-性能基线.md                      实验一、二的数据与详细分析
│   └── 03-知识库规模对推理速度的影响.md      实验三
├── scripts/
│   ├── 01-重启服务并开日志.sh              重启推理服务 + 打开性能日志
│   ├── 02-重置root密码.sh                  通过 adb 提权重置密码
│   ├── 03-连接板子.ps1                     一键建立 adb 端口转发
│   ├── 04-测试SSH登录.py                   验证密码/密钥登录
│   ├── 05-记录板子状态.sh                  每秒记录温度/NPU/内存（排查重启）
│   ├── 06-重启后端.sh                      改完后端代码后重启 uvicorn
│   ├── 07-采样DDR频率.sh                   验证内存频率是否拉满
│   ├── 08-扫描损坏文件.sh                  扫描硬重启导致的"全零文件"
│   ├── 09-导出字节码结构.py                 从 .pyc 导出代码结构
│   ├── 10-反汇编pyc.py                     从 .pyc 反汇编，用于源码恢复
│   ├── 11-测试上下文长度影响.py             实验三
│   ├── 12-测试采样参数效果.py               实验四
│   └── 13-检查报告忠实度.py                 校验报告对知识库的覆盖率
├── backend/
│   ├── import_kg.py                       CSV → Neo4j 导入脚本
│   ├── services/report_service.py         提示词模板（已优化）
│   ├── services/kg_service.RECOVERED.py   知识图谱服务（从字节码重建）
│   └── services/kg_service.pyc            字节码备份
└── .gitignore
```

> **模型文件与 SDK 未上传**（单个文件超 GitHub 100 MB 限制）。
> 获取方式见 `docs/01-环境与部署清单.md` 里的分享链接（提取码 `rkllm`）。

---

## 九、复现步骤

```bash
# 1. 连接开发板（adb 端口转发）
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/03-连接板子.ps1

# 2. 打开推理性能日志
adb shell "sh /userdata/rkllm/bench_start.sh"
adb forward tcp:18080 tcp:8080

# 3. 复现实验三（上下文长度影响）
python scripts/11-测试上下文长度影响.py
adb shell "grep -E 'Prefill|Generate' /userdata/rkllm/bench.log"

# 4. 复现实验四（采样参数）
adb forward tcp:18081 tcp:8081
python scripts/12-测试采样参数效果.py
python scripts/13-检查报告忠实度.py
```

---

## 十、故障与踩坑记录

### 1. 硬重启导致源文件损坏（重要）

开发板在高负载推理下会随机重启/卡死（累计 4 次）。**硬断电会导致 ext4 文件系统损坏**：

```
[损坏] 18852 字节全零: /userdata/backend/app/services/kg_service.py
[损坏]  1788 字节全零: /userdata/backend/app/models/schemas.py
```

文件大小和修改时间还在，但内容全部变成 `0x00`——这是 ext4 延迟分配的经典场景
（元数据进了日志，数据块没落盘）。

**恢复方法**：Python 的 **sourceless import** —— 移走损坏的 `.py`，
Python 会退回加载同目录的 `.pyc` 字节码，服务立刻恢复。
进一步从字节码**反汇编重建了源码**（`kg_service.RECOVERED.py`）。

排查工具见 `scripts/08-扫描损坏文件.sh`。

### 2. Python stdout 缓冲导致日志丢失

`stdout` 重定向到文件时是**块缓冲**的，进程被硬杀时缓冲区内容全部丢失，
导致崩溃前的日志拿不到。解决：启动脚本里加 `export PYTHONUNBUFFERED=1`。

### 3. RKLLM 的性能配置脚本从未生效

`flask_server.py` 启动时会调用 `sudo bash fix_freq_rk3588.sh` 把各部件锁到性能模式，
但 Buildroot 系统**没有 `sudo`**：

```
/bin/sh: line 1: sudo: command not found
```

而且该脚本文件本身也不存在。所以官方的性能配置从未应用。

### 4. NPU 驱动版本偏低

```
W rkllm: Warning: Your rknpu driver version is too low, please upgrade to 0.9.7
```

当前 0.9.6，官方要求 0.9.7+。可通过 `cat /sys/kernel/debug/rknpu/version` 查询。

### 5. Windows 文件名不区分大小写

目录重组时 `SDK` 和 `sdk` 被当成同一个目录，导致文件被误归档。

---

## 十一、后续工作

- [ ] 升级 RKLLM runtime 1.2.3 → 1.3.0
- [ ] 查询层加 `WHERE severity >= 3` + `LIMIT`，防止知识库膨胀拖慢 prefill
- [ ] 做 0.8B / 4B 对比实验（同一块板子，验证"模型大小 ↔ 速度"线性关系）
- [ ] 评估 W4A16 量化（内存减半，速度约翻倍）
- [ ] 排查并解决高负载下的重启问题（怀疑电源余量不足：12V/2.5A 仅 50% 余量）

---

## 十二、参考资料

- [RKLLM 官方仓库](https://github.com/airockchip/rknn-llm)
- Qwen3-4B 模型配置（算显存用）：`https://hf-mirror.com/Qwen/Qwen3-4B/raw/main/config.json`
