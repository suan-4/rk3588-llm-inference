# 一键连接板子：检查 adb 设备 -> 建立端口转发 -> 自检
#
# 用法（在 PowerShell 里）：
#   powershell -ExecutionPolicy Bypass -File scripts\03-连接板子.ps1
#
# 跑完之后就可以用 `ssh rk3588`，或让 MobaXterm 连 127.0.0.1:2222

$ErrorActionPreference = "Continue"
$adb = "D:\application\platform-tools\adb.exe"

if (-not (Test-Path $adb)) {
    Write-Host "找不到 adb：$adb" -ForegroundColor Red
    exit 1
}

Write-Host "[1/4] 检查 adb 设备..." -ForegroundColor Cyan
$devices = & $adb devices 2>&1 | Out-String
$online = @(($devices -split "`r?`n") | Where-Object { $_ -match "\tdevice" })

if (-not $online) {
    Write-Host "  没找到设备。请拔插一次 USB 线，等 10 秒后重跑本脚本。" -ForegroundColor Yellow
    Write-Host "  当前 adb 输出：" -ForegroundColor DarkGray
    Write-Host $devices
    exit 1
}

$serial = @($online[0] -split "\t")[0].Trim()
Write-Host "  设备: $serial" -ForegroundColor Green

Write-Host "[2/4] 建立端口转发 2222 -> 板子 22 ..." -ForegroundColor Cyan
& $adb forward tcp:2222 tcp:22 | Out-Null
& $adb forward tcp:18080 tcp:8080 | Out-Null   # RKLLM 推理接口
& $adb forward tcp:18081 tcp:8081 | Out-Null   # 后端接口
& $adb forward --list

Write-Host "[3/4] 测试 SSH ..." -ForegroundColor Cyan
$r = & ssh -o BatchMode=yes -o ConnectTimeout=8 rk3588 "echo CONNECT_OK; cat /sys/kernel/debug/rknpu/version" 2>&1 | Out-String
if ($r -match "CONNECT_OK") {
    Write-Host "  SSH 免密登录正常" -ForegroundColor Green
    ($r -split "`n") | Where-Object { $_ -match "RKNPU" } | ForEach-Object { Write-Host ("  " + $_.Trim()) }
} else {
    Write-Host "  SSH 测试未通过：" -ForegroundColor Yellow
    Write-Host $r
}

Write-Host "[4/4] 完成" -ForegroundColor Cyan
Write-Host ""
Write-Host "现在可以：" -ForegroundColor White
Write-Host "  ssh rk3588                    进板子终端"
Write-Host "  MobaXterm -> SSH 127.0.0.1:2222 (root / 密钥)"
Write-Host "  推理接口 http://127.0.0.1:18080/rkllm_chat"
Write-Host "  后端接口 http://127.0.0.1:18081"
