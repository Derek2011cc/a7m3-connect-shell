#!/bin/bash
# Install Python dependencies and vendor Sony-PMCA-RE.
# Run inside WSL as root (setup.ps1 does this for you).
set -e
cd "$(dirname "$0")"

PY=python3
if ! command -v "$PY" >/dev/null 2>&1; then
    echo "python3 未安装：sudo apt install -y python3 python3-pip" >&2
    exit 1
fi

if "$PY" -m pip install --break-system-packages -r requirements.txt 2>/dev/null; then
    :
else
    "$PY" -m pip install --user -r requirements.txt
fi

if [ ! -d vendor/Sony-PMCA-RE/pmca ]; then
    mkdir -p vendor
    if command -v git >/dev/null 2>&1; then
        echo "cloning Sony-PMCA-RE ..."
        git clone --depth 1 https://github.com/ma1co/Sony-PMCA-RE vendor/Sony-PMCA-RE
    else
        echo "git 不可用，改用 zip 下载 ..."
        "$PY" - <<'PY'
import io
import os
import shutil
import urllib.request
import zipfile

url = "https://codeload.github.com/ma1co/Sony-PMCA-RE/zip/refs/heads/master"
data = urllib.request.urlopen(url, timeout=180).read()
z = zipfile.ZipFile(io.BytesIO(data))
os.makedirs("vendor", exist_ok=True)
z.extractall("vendor")
shutil.move("vendor/Sony-PMCA-RE-master", "vendor/Sony-PMCA-RE")
PY
    fi
fi

"$PY" -c "import usb, Cryptodome; print('python deps ok')"
"$PY" -c "import sys; sys.path.insert(0, 'vendor/Sony-PMCA-RE'); import pmca; print('pmca ok')"
echo ""
echo "setup done. Next:"
echo "  1) camera: USB connection = Mass Storage"
echo "  2) Windows: .\\cam-shell.cmd cmd \"uname -a\""
