#!/bin/sh
# 重启 RKLLM flask 服务，并打开性能日志
#
# 用途：测量 TTFT / tokens/s / 内存占用
# 用法：sh /userdata/rkllm/bench_start.sh
#
# 注意：会短暂中断大屏上的对话功能（约 5-15 秒，取决于模型加载速度）

MODEL=/userdata/rkllm/Qwen3-4B-Instruct-2507_W8A8_RK3588.rkllm
SERVER=/userdata/rkllm/flask_server.py
LOGPATH=/userdata/rkllm/bench.log

echo "== 1. 停掉旧的 flask 服务 =="
pkill -f flask_server.py 2>/dev/null
sleep 2
if pgrep -f flask_server.py > /dev/null 2>&1; then
    echo "   旧进程还在，强杀"
    pkill -9 -f flask_server.py 2>/dev/null
    sleep 2
fi
echo "   done"

echo "== 2. 记录基线内存 =="
free -m

echo "== 3. 启动（RKLLM_LOG_LEVEL=1） =="
echo "start $(date '+%Y-%m-%d %H:%M:%S')  baseline:" > "$LOGPATH"
free -m >> "$LOGPATH"

cd /userdata/rkllm
export RKLLM_LOG_LEVEL=1
export PYTHONUNBUFFERED=1
nohup python3 "$SERVER" --rkllm_model_path "$MODEL" --target_platform rk3588 >> "$LOGPATH" 2>&1 &

echo "   日志写到 $LOGPATH"
echo "   等待模型加载..."
sleep 8

echo "== 4. 加载后的内存 =="
free -m

echo "== 5. NPU 负载 =="
cat /sys/kernel/debug/rknpu/load 2>/dev/null

echo ""
echo "完成。现在可以去调 API 了。"
