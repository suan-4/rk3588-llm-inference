#!/bin/sh
# 后台每秒记录一次板子状态，写到 /userdata/watch.log
#
# /userdata 是持久化的，所以板子重启后日志还在。
# 用途：定位"跑着跑着突然重启"的原因——看重启前最后几行。
#
# 启动：nohup sh /userdata/watch.sh > /dev/null 2>&1 &
# 停止：killall watch.sh   （或 pkill -f watch.sh）
# 查看：tail -20 /userdata/watch.log

LOG=/userdata/watch.log

if [ "$1" = "stop" ]; then
    pkill -f "watch.sh" 2>/dev/null
    echo "已停止监控"
    exit 0
fi

echo "===== monitor start, uptime=$(cut -d' ' -f1 /proc/uptime)s =====" >> "$LOG"

while true; do
    UP=$(cut -d' ' -f1 /proc/uptime)
    T0=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null)
    T1=$(cat /sys/class/thermal/thermal_zone1/temp 2>/dev/null)
    T2=$(cat /sys/class/thermal/thermal_zone2/temp 2>/dev/null)
    C4=$(cat /sys/devices/system/cpu/cpufreq/policy4/scaling_cur_freq 2>/dev/null)
    C6=$(cat /sys/devices/system/cpu/cpufreq/policy6/scaling_cur_freq 2>/dev/null)
    MEM=$(free -m | awk '/Mem:/ {print $3 "M used / " $7 "M avail"}')
    LOAD=$(cat /sys/kernel/debug/rknpu/load 2>/dev/null)
    echo "up=${UP}s soc=${T0} big0=${T1} big1=${T2} cpu4=${C4} cpu6=${C6} mem=${MEM} ${LOAD}" >> "$LOG"
    sleep 1
done
