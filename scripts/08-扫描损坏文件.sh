#!/bin/sh
# 扫描 /userdata 下"全零"的文件（硬重启导致的数据损坏）
#
# 原理：正常文件里不可能全是 0x00。用 tr 删掉所有 \0 后如果长度变成 0，
#       说明这个文件整块数据都丢了。
# 用法：sh /userdata/scan_corrupt.sh [扫描目录，默认 /userdata]

DIR=${1:-/userdata}

echo "扫描目录: $DIR"
echo "=========================================="

find "$DIR" -type f -size +0c 2>/dev/null | while read -r f; do
    # 跳过体积很大的模型/压缩包，太慢
    SIZE=$(stat -c %s "$f" 2>/dev/null)
    if [ -z "$SIZE" ] || [ "$SIZE" -gt 50000000 ]; then
        continue
    fi
    NONZERO=$(tr -d '\000' < "$f" 2>/dev/null | wc -c)
    if [ "$NONZERO" -eq 0 ]; then
        echo "[损坏] $SIZE 字节全零: $f"
    fi
done

echo "=========================================="
echo "扫描完成"
