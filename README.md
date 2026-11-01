# a7m3-connect-shell

通过 USB **Senser 服务模式**连接 Sony A7M3（ILCE-7M3），在相机上执行命令、上传/下载文件。

> **只在你自己的设备上使用。** 这是 root shell，写操作可能损坏相机；作者不承担任何责任。
> 本仓库不包含 Sony 固件、密钥或相机转储。

## 功能

| 命令 | 作用 |
|---|---|
| `raw` | 逐行命令模式（无 `cam>` 前缀，直接输入命令） |
| `cmd "<命令>"` | 执行一条命令并打印输出 |
| `push <本地> <远端>` | 上传文件（如 `/tmp/v.so`） |
| `pull <远端> <本地>` | 下载文件 |
| `shell` | PMCA 平台 shell（`help` / `shell` / `push` / `pull`） |

工具会自动完成：

1. 检查相机是否 attach 到 WSL；
2. 相机在 **Mass Storage**（`054c:0c02`）时自动切换到 **服务模式**（`054c:0336`）；
3. 用 Sony 的 Senser 两阶段认证（PMCA）打开相机终端；
4. 会话结束后让相机回到 `054c:0c02`。

## 原理

```
Windows: usbipd-win 把相机 USB 直通给 WSL2
        ↓
WSL: PMCA (Sony-PMCA-RE) 发送 StartSenser + 3 轮质询应答
        ↓
相机重枚举为 054c:0336（服务模式）
        ↓
再认证一次 → 打开 Senser 终端 channel → 在相机上执行命令
```

Windows 端**不需要 Zadig**、不需要替换海量存储驱动——USB 直通由 usbipd-win 完成。

## 环境要求

- Windows 10/11，已安装 **WSL2**（Ubuntu）；
- **usbipd-win**（`winget install usbipd-win`）；
- WSL 内 Python 3.8+；
- 相机 USB 连接方式设为 **大量存储（Mass Storage）**，不是 MTP/Auto；
- 网络可访问 GitHub（首次安装会下载 PMCA）。

## 安装

### 1. 安装 WSL2 与 usbipd-win（Windows）

管理员 PowerShell：

```powershell
wsl --install
winget install usbipd-win
```

装完重启一次。

### 2. 获取本仓库

把整个 `a7m3-connect-shell` 目录放到 Windows 任意路径，例如：

```
F:\tools\a7m3-connect-shell
```

### 3. 安装 WSL 依赖 + PMCA

在仓库目录运行：

```powershell
.\setup.cmd
```

它会：

- 在 WSL（root）里安装 `requirements.txt` 的 Python 依赖；
- 把 [Sony-PMCA-RE](https://github.com/ma1co/Sony-PMCA-RE) 克隆到 `vendor/Sony-PMCA-RE`；
- 自检 `usb` / `Cryptodome` / `pmca` 是否可用。

Linux 下等价命令：

```bash
sudo ./setup.sh
```

### 4. 连接相机

相机菜单：**USB → USB 连接 → 大量存储**，然后插 USB。
`usbipd list` 应看到 `054c:0c02`。

## 使用

```bat
cam-shell.cmd cmd "uname -a"
cam-shell.cmd cmd "ls -l /usr/scenario" --seconds 5
```

```bat
cam-shell.cmd raw
```

`raw` 是逐行模式（没有 `cam>` 前缀）：

```
/usr/share/app # ls
bin  initrd  log  sbin  tmp  usr  ...
/usr/share/app #
```

输入 `exit` 或 `quit` 退出。

```bat
cam-shell.cmd push payload\vfm2.so /tmp/v.so
cam-shell.cmd cmd "/usr/bin/scenario.elf /tmp/v.so b:0x01" --seconds 8
```

```bat
cam-shell.cmd pull /tmp/result.bin .\result.bin
```

## 故障排查

| 现象 | 处理 |
|---|---|
| `No devices found` | 相机没 attach 到 WSL：运行一次 `cam-shell.cmd`，或手动 `usbipd attach --wsl --busid <BUSID>` |
| `service mode did not appear` | usbipd 自动 attach 循环没在跑；重新运行 `cam-shell.cmd`，确认 `usbipd list` 状态为 `Attached` |
| 相机不在 `usbipd list` | 相机不是“大量存储”模式、换 USB 口/线、重新插拔 |
| 退出后相机没回到 `0c02` | 拔插一次 USB；Windows 盘符会恢复 |
| `PMCA not found` | 运行 `setup.ps1`，或设置 `PMCA_PATH` 指向 Sony-PMCA-RE 目录 |
| `Permission denied` | 通过 `cam-shell.cmd`（内部以 root 运行 WSL）；Linux 用 `sudo` |

## 已验证环境

- ILCE-7M3，固件 4.03；
- Windows 11 + WSL2 Ubuntu；
- usbipd-win 5.3；
- Sony-PMCA-RE master。

已验证：`uname -a`、`ls`、`push` + `cat` 回读。**未验证**：不同固件/机型的 PID、Linux 原生 usbip 路径。

## 安全与边界

- 服务模式是 **root**，不要执行 `FORMAT`、`FIRMUP`、`mkfs`、工厂重置等写操作；
- 进入服务模式后相机盘符会消失，退出后恢复；
- `push` 到 `/tmp` 是 tmpfs，重启即消失；
- 不包含任何 Sony 固件/密钥；PMCA 由 `setup` 单独下载（MIT）。

## 目录

```
cam_shell.py      主程序（认证 + 终端/文件操作）
cam-shell.cmd     Windows 入口
cam-shell.ps1     usbipd 检查/自动 attach + 转 WSL
cam-shell.sh      Linux/WSL 入口
setup.ps1         Windows 一键安装
setup.sh          WSL 依赖 + PMCA 安装
requirements.txt  Python 依赖
LICENSE           MIT
```

## 许可

本仓库代码 MIT。依赖 [Sony-PMCA-RE](https://github.com/ma1co/Sony-PMCA-RE)（MIT）与
[usbipd-win](https://github.com/dorssel/usbipd-win)（GPL-3.0），各自遵循其许可证。
