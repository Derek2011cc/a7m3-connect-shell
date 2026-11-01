param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ToolArgs
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$tool = Join-Path $root "cam_shell.py"

$usbipd = Join-Path $env:ProgramFiles "usbipd-win\usbipd.exe"
if (-not (Test-Path $usbipd)) {
    throw "usbipd-win 未安装。请先运行: winget install usbipd-win"
}
if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    throw "未找到 WSL2。请先在管理员 PowerShell 运行: wsl --install"
}

function Get-CameraLine {
    $list = & $usbipd list 2>$null
    return ($list | Select-String '054c:' | Select-Object -First 1)
}

$line = Get-CameraLine
if (-not $line) {
    throw "未找到 Sony 相机。请用 USB 连接相机，并把 USB 连接方式设为'大量存储'(Mass Storage)。"
}

# Keep exactly one auto-attach loop (needed when 0c02 re-enumerates as 0336).
$loops = @(Get-CimInstance Win32_Process -Filter "Name='usbipd.exe'" |
           Where-Object { $_.CommandLine -match ' attach ' })
if ($loops.Count -eq 0) {
    $busid = ($line.ToString().Trim() -split '\s+')[0]
    Write-Host "starting usbipd auto-attach for $busid ..."
    Start-Process -FilePath $usbipd `
        -ArgumentList "attach --wsl --busid $busid --auto-attach" `
        -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

$attached = $false
for ($i = 0; $i -lt 20; $i++) {
    $line = Get-CameraLine
    if ($line -and $line.ToString() -match 'Attached') {
        $attached = $true
        break
    }
    Start-Sleep -Milliseconds 500
}
if (-not $attached) {
    throw "相机没有 attach 到 WSL。请在 PowerShell 运行: usbipd attach --wsl --busid <BUSID>"
}

$drive = $tool.Substring(0, 1).ToLower()
$wslTool = "/mnt/$drive" + ($tool.Substring(2) -replace "\\", "/")
wsl.exe -u root -e python3 $wslTool @ToolArgs
exit $LASTEXITCODE
