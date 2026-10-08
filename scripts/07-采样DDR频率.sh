#!/bin/sh
# 采样 DDR 内存控制器和 NPU 的运行频率
#
# 用途：验证"decode 阶段受内存带宽限制"——看推理时 DDR 跑到什么频率
# 用法：sh /userdata/sample_freq.sh [采样秒数，默认 90]
#
# 输出三列：运行秒数、DDR频率(Hz)、NPU频率(Hz)

DURATION=${1:-90}
LOG=/userdata/dmc_sample.log

echo "uptime_sec dmc_freq_hz npu_freq_hz" > "$LOG"

i=0
while [ "$i" -lt "$DURATION" ]; do
    UP=$(cut -d' ' -f1 /proc/uptime)
    DMC=$(cat /sys/class/devfreq/dmc/cur_freq 2>/dev/null)
    NPU=$(cat /sys/class/devfreq/fdab0000.npu/cur_freq 2>/dev/null)
    echo "$UP $DMC $NPU" >> "$LOG"
    sleep 1
    i=$((i + 1))
done

echo "采样结束，共 $DURATION 条，写入 $LOG"
echo "DDR 频率分布："
awk 'NR>1 {print $2}' "$LOG" | sort | uniq -c | sort -rn
