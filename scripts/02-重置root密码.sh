#!/bin/sh
# 重置板子 root 密码
#
# 前提：能通过 adb shell 进去（adb 是 root 权限，不需要密码）
# 用法：sh /userdata/reset_root_pw.sh [新密码]
#       不传参数则默认设为 rk3588

NEWPW="${1:-rk3588}"

echo "== 1. 备份 /etc/shadow =="
BACKUP="/etc/shadow.bak.$(date +%Y%m%d%H%M%S)"
cp /etc/shadow "$BACKUP"
echo "   备份到 $BACKUP"

echo "== 2. 生成新哈希（sha256） =="
NEWHASH=$(mkpasswd -m sha256 "$NEWPW")
if [ -z "$NEWHASH" ]; then
    echo "   生成失败，中止"
    exit 1
fi
echo "   $NEWHASH"

echo "== 3. 更新 /etc/shadow =="
awk -F: -v h="$NEWHASH" 'BEGIN{OFS=":"} { if ($1=="root") $2=h; print }' /etc/shadow > /tmp/shadow.new

if [ ! -s /tmp/shadow.new ]; then
    echo "   生成的新文件为空，中止（原文件未动）"
    rm -f /tmp/shadow.new
    exit 1
fi

# 行数必须和原来一致，防止写坏
OLDN=$(wc -l < /etc/shadow)
NEWN=$(wc -l < /tmp/shadow.new)
if [ "$OLDN" != "$NEWN" ]; then
    echo "   行数不一致（原 $OLDN 行，新 $NEWN 行），中止"
    rm -f /tmp/shadow.new
    exit 1
fi

cat /tmp/shadow.new > /etc/shadow
chmod 600 /etc/shadow
chown root:root /etc/shadow
rm -f /tmp/shadow.new
echo "   写入完成"

echo "== 4. 校验 =="
awk -F: '$1=="root" { print "   root: " substr($2,1,25) "..." }' /etc/shadow
echo ""
echo "新密码：$NEWPW"
echo "登录后可以用 passwd 命令改成自己的密码。"
