#!/usr/bin/env bash
# 手机 → 电脑剪贴板 · 一键启动
# 用法:
#   ./start.sh              # 默认端口 8686
#   ./start.sh -p 9090      # 透传给 server.py 的任意参数均可
set -euo pipefail
cd "$(dirname "$0")"

# 1. 检查 python3
if ! command -v python3 >/dev/null 2>&1; then
    echo "✗ 未找到 python3，请先安装 Python 3"
    exit 1
fi

# 2. 预检剪贴板后端（wl-copy / xclip / xsel / pbcopy / pyperclip 任一即可）
backend=""
for t in wl-copy xclip xsel pbcopy; do
    command -v "$t" >/dev/null 2>&1 && { backend="$t"; break; }
done
if [ -z "$backend" ] && python3 -c "import pyperclip" >/dev/null 2>&1; then
    backend="pyperclip"
fi
if [ -z "$backend" ]; then
    echo "✗ 未找到剪贴板后端，请先安装其中之一："
    echo "    sudo apt install xclip          # X11"
    echo "    sudo apt install wl-clipboard   # Wayland"
    echo "    pip install pyperclip"
    exit 1
fi
echo "✓ 剪贴板后端: $backend"

# 3. 启动（前台运行，Ctrl+C 停止；参数原样透传给 server.py）
exec python3 server.py "$@"
