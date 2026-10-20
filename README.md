# phone-clipboard

> 手机输入 → 电脑剪贴板。手机和电脑连同一局域网，用手机浏览器打开一个网页，输入的内容在停顿 1 秒后自动出现在电脑剪贴板里，直接在电脑上粘贴即可。

单文件、零第三方依赖（仅 Python 3 标准库），适合在 Linux / macOS 上一键启动。

## 为什么需要它

在电脑上工作时偶尔需要在手机上查到的验证码、口令、中文长文本传到电脑。常见做法是登录微信/QQ 给自己发消息，步骤多且会留在聊天记录里。本工具把这条路径缩短为：

1. 电脑上启动 `./start.sh`
2. 手机浏览器打开启动时显示的地址（或扫码）
3. 输入，停顿 1 秒 —— 电脑剪贴板已就绪

## 功能特性

- **自动推送**：输入停顿 1 秒自动复制；页面失焦（切换到电脑前）立即推送兜底
- **连接状态实时可见**：页面每 3 秒心跳检测，未连接会明确标红提示
- **零依赖**：仅需 Python 3 标准库；剪贴板后端自动探测
- **免剪贴板历史**（Linux + GTK4 可用时）：写入时附带 `x-kde-passwordManagerHint` 提示，Copyous / Klipper 等剪贴板历史工具不会记录这些内容，粘贴不受任何影响
- **手机键盘自适应**：基于 `visualViewport` 的可视视口适配，键盘弹出/收起、旋转屏幕时页面完整可见
- **多平台剪贴板后端**：GTK4 → wl-copy (Wayland) → xclip / xsel (X11) → pbcopy (macOS) → pyperclip 逐级回退
- **可选二维码**：安装 `qrcode` 库后，启动时在终端直接打印扫码地址

## 环境要求

| 依赖 | 要求 |
|---|---|
| Python | ≥ 3.8（仅需标准库） |
| 剪贴板后端（Linux X11） | `xclip` 或 `xsel` |
| 剪贴板后端（Linux Wayland） | `wl-clipboard`（`wl-copy`） |
| 剪贴板后端（macOS） | 系统自带 `pbcopy` |
| 增强（可选） | GTK4 (`gi`)、`pyperclip`、`qrcode` |

Debian/Ubuntu 安装后端示例：

```bash
# X11
sudo apt install xclip
# Wayland
sudo apt install wl-clipboard
# 可选增强
pip install --user qrcode
```

## 快速开始

```bash
git clone https://github.com/Howardzhangdqs/phone-clipboard.git
cd phone-clipboard
./start.sh                # 默认端口 8686
# 或: python3 server.py -p 9090
```

启动后会打印局域网地址，例如：

```
═  手机 → 电脑剪贴板  已启动
  剪贴板后端: gtk4+免历史提示
  手机连同一 Wi-Fi，用手机浏览器打开:
    http://192.168.1.23:8686
```

手机浏览器打开该地址即可使用。`Ctrl+C` 停止。

## 命令行参数

```
usage: server.py [-h] [-p PORT] [-b BIND]

options:
  -p, --port   监听端口（默认 8686）
  -b, --bind   监听地址（默认 0.0.0.0；可用 127.0.0.1 限制为本机访问，
               配合 SSH 端口转发使用，见下文"安全"一节）
```

`start.sh` 会透传所有参数给 `server.py`，例如 `./start.sh -p 9090 -b 127.0.0.1`。

## HTTP API

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/` | 网页界面 |
| `GET` | `/api/ping` | 健康检查，返回 `{"ok": true, "tool": "<后端名>"}` |
| `POST` | `/api/copy` | 请求体 `{"text": "..."}`，写入剪贴板，返回 `{"ok": bool, "tool": str, "error": str}` |

限制：请求体上限 10 MiB（超出返回 `413`）；`text` 必须为字符串，空字符串不修改剪贴板。

## 架构与剪贴板后端

```
手机浏览器 ──HTTP──▶ server.py (ThreadingHTTPServer)
                        │
                        ├─ 首选: _clip_writer.py (GTK4, 强制 X11 后端)
                        │    写入时同时提供 text/* 与 x-kde-passwordManagerHint，
                        │    剪贴板历史工具 (Copyous/Klipper) 依提示不记录
                        │
                        ├─ 回退: wl-copy → xclip → xsel → pbcopy (子进程)
                        └─ 最终回退: pyperclip (如已安装)
```

- `_clip_writer.py` 以独立进程运行：成功则持有剪贴板所有权常驻（他人覆写或 1 小时后退出，不堆积进程）；GTK4/显示不可用时以退出码 `3` 立即失败，`server.py` 自动改用下一级后端
- 服务端主动关闭空闲 30 秒的 keep-alive 连接，并对手机锁屏产生的 `ConnectionReset` 静默处理，避免日志噪音

## 安全模型

**本工具没有任何鉴权**。凡能访问该端口的设备都可以向你的电脑剪贴板写入内容。请阅读 [SECURITY.md](SECURITY.md) 了解威胁模型与建议对策，要点：

- 仅在**可信局域网**内使用；不可信网络（公共 Wi-Fi、宿舍网等）请勿开放端口
- 或用 `-b 127.0.0.1` 只监听本机，经 SSH 隧道访问（`ssh -L 8686:127.0.0.1:8686 user@pc`）
- 服务日志只记录内容**长度**与所用后端，不记录剪贴板内容本身

## 开机自启（systemd 用户服务示例）

```ini
# ~/.config/systemd/user/phone-clipboard.service
[Unit]
Description=phone-clipboard (手机 → 电脑剪贴板)

[Service]
ExecStart=/usr/bin/python3 /path/to/phone-clipboard/server.py -p 8686
Restart=on-failure

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now phone-clipboard.service
```

注意：若使用 GTK4 写入器，需保证该用户会话有图形环境（`DISPLAY`）；以 SSH 无头会话运行时将自动回退到 wl-copy/xclip 等后端。

## 故障排查

| 现象 | 处理 |
|---|---|
| 手机打不开页面 | 确认同一 Wi-Fi；检查电脑防火墙（`sudo ufw status`）；换端口重试 |
| 页面显示"未连接" | 服务是否仍在运行；端口是否被占用（`ss -tlnp | grep 8686`） |
| 复制失败：未找到剪贴板后端 | 安装 `xclip` / `wl-clipboard` 之一，或 `pip install pyperclip` |
| Wayland 下 GTK4 写入失败 | 已知限制：无头 Wayland 的 `set_selection` 会被 mutter 拒绝，程序会自动回退 |
| 内容进入剪贴板历史 | GTK4 写入器未生效（无图形环境/GTK4），此时走 wl-copy/xclip，属正常行为 |

## 路线图

- [ ] 可选的一次性访问令牌（查询参数鉴权）
- [ ] 电脑 → 手机方向的回传
- [ ] Docker 镜像

## 贡献与许可

- 贡献指南见 [CONTRIBUTING.md](CONTRIBUTING.md)，变更记录见 [CHANGELOG.md](CHANGELOG.md)
- 本项目以 [MIT License](LICENSE) 发布
