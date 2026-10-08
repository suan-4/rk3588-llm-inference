#!/usr/bin/env python3
"""测试板子 SSH 的密码登录 / 密钥登录是否正常。

用法：
    python scripts/04-测试SSH登录.py
    python scripts/04-测试SSH登录.py --password 你的密码
"""

import argparse
import os
import sys

import paramiko


def try_login(host, port, user, password=None, keyfile=None, label=""):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs = {
        "hostname": host,
        "port": port,
        "username": user,
        "timeout": 10,
        "banner_timeout": 15,
        "auth_timeout": 15,
        "allow_agent": False,
        "look_for_keys": False,
    }
    if password is not None:
        kwargs["password"] = password
    if keyfile:
        kwargs["key_filename"] = keyfile

    print(f"--- {label} ---")
    try:
        client.connect(**kwargs)
    except paramiko.AuthenticationException as e:
        print(f"  [失败] 认证被拒: {e}")
        return False
    except Exception as e:
        print(f"  [失败] {type(e).__name__}: {e}")
        return False

    stdin, stdout, stderr = client.exec_command("whoami; hostname; cat /sys/kernel/debug/rknpu/version")
    out = stdout.read().decode(errors="replace").strip()
    print("  [成功]")
    for line in out.splitlines():
        print("    " + line)
    client.close()
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=2222)
    ap.add_argument("--user", default="root")
    ap.add_argument("--password", default=None)
    ap.add_argument("--key", default=os.path.expanduser(r"~\.ssh\rk3588_board_ed25519"))
    args = ap.parse_args()

    ok = False

    # 1) 密钥登录
    if os.path.exists(args.key):
        ok |= try_login(args.host, args.port, args.user, keyfile=args.key, label="密钥登录")
    else:
        print(f"--- 密钥登录 ---\n  跳过，找不到 {args.key}")

    # 2) 密码登录
    pwd = args.password
    if pwd is None:
        pwd = "rk3588"
        print(f"--- 密码登录（用默认值 {pwd}） ---")
    else:
        print("--- 密码登录 ---")
    try:
        ok |= try_login(args.host, args.port, args.user, password=pwd, label="密码认证")
    except Exception:
        pass

    print()
    print("结论：" + ("至少一种方式可用" if ok else "两种都失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
