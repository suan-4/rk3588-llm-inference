#!/bin/sh
# 重启电梯项目的后端（FastAPI / uvicorn）
#
# 改完 /userdata/backend 里的代码后跑这个，改动才会生效。
# 用法：sh /userdata/restart_backend.sh

APP_DIR=/userdata/backend
LOG=/userdata/backend_uvicorn.log

echo "== 1. 停掉旧的后端进程 =="
pkill -f "uvicorn app.main" 2>/dev/null
sleep 2
if pgrep -f "uvicorn app.main" > /dev/null 2>&1; then
    echo "   还在，强杀"
    pkill -9 -f "uvicorn app.main" 2>/dev/null
    sleep 2
fi
echo "   done"

echo "== 2. 启动 =="
cd "$APP_DIR" || { echo "   进不去 $APP_DIR"; exit 1; }
export PYTHONUNBUFFERED=1
echo "" >> "$LOG"
echo "===== restart $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$LOG"
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8081 >> "$LOG" 2>&1 &

echo "   等待启动..."
sleep 6

echo "== 3. 检查 =="
if pgrep -f "uvicorn app.main" > /dev/null 2>&1; then
    echo "   后端已启动 ✅"
    ps -ef | grep "uvicorn app.main" | grep -v grep
else
    echo "   启动失败 ❌，日志尾部："
    tail -25 "$LOG"
    exit 1
fi

echo ""
echo "日志：$LOG"
