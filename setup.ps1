param()

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$setup = Join-Path $root "setup.sh"

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    throw "未找到 WSL2。请先在管理员 PowerShell 运行: wsl --install"
}

$usbipd = Join-Path $env:ProgramFiles "usbipd-win\usbipd.exe"
if (-not (Test-Path $usbipd)) {
    Write-Host "usbipd-win 未安装。"
    Write-Host "请运行: winget install usbipd-win"
    Write-Host "或从 https://github.com/dorssel/usbipd-win/releases 下载安装。"
} else {
    Write-Host "usbipd-win: $usbipd"
}

$drive = $setup.Substring(0, 1).ToLower()
$wslSetup = "/mnt/$drive" + ($setup.Substring(2) -replace "\\", "/")

Write-Host "installing Python deps + Sony-PMCA-RE inside WSL (root) ..."
wsl.exe -u root -e bash $wslSetup

Write-Host ""
Write-Host "setup finished."
Write-Host "Camera: USB connection = Mass Storage, then run:"
Write-Host '  .\cam-shell.cmd cmd "uname -a"'
