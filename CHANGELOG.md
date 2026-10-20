# Changelog

本项目的所有显著变更都记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本 SemVer](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [0.2.0] - 2026-10-20

### 修复
- **剪贴板后端按会话类型选择**：X11 会话不再误用 wl-copy（装了也连不上 Wayland），
  Wayland 会话优先 wl-copy，X11 会话用 xclip/xsel，macOS 用 pbcopy。
- **写入校验**：所有 CLI 后端检查子进程返回码并读回剪贴板比对，
  失败自动切换下一后端；彻底消除"实际写入失败却报 ok:true"的静默错误。
- GTK4 写入器改为"存活 + 读回一致"双条件判定成功，1.5 秒内快速失败进链回退。
- `lan_ips()` 过滤 RFC 2544 网段（198.18.0.0/15），修复代理 TUN (fake-ip) 环境下
  启动横幅打印不可用地址的问题。
- 复制失败时 API 返回逐后端的失败原因（如 `wl-copy(rc=1)`），便于排查。

### 变更
- `GET /api/ping` 响应字段 `tool` 改为 `chain`（完整后端链描述）。
- 启动横幅显示会话类型与完整后端链。

## [0.1.0] - 2026-09-27

首个可用版本。

### 新增
- 单文件零依赖服务器 `server.py`：网页输入 → 停顿 1 秒/失焦自动推送至电脑剪贴板。
- 一键启动脚本 `start.sh`：环境预检（python3、剪贴板后端）后透传参数启动。
- GTK4 剪贴板写入器 `_clip_writer.py`：写入时附带 `x-kde-passwordManagerHint`，
  剪贴板历史工具（Copyous/Klipper）不记录，粘贴不受影响；强制 X11 后端以绕过
  无头 Wayland 下 mutter 的 serial 校验限制。
- 多级剪贴板后端回退链：GTK4 → wl-copy → xclip → xsel → pbcopy → pyperclip。
- 手机端页面：`visualViewport` 可视视口自适应（键盘弹出/旋转），3 秒心跳连接状态，
  清空按钮（不推送空内容）。
- 服务端健壮性：10 MiB 请求体上限、空内容跳过、keep-alive 30 秒空闲回收、
  对端断开异常静默、可选终端二维码（安装 qrcode 库时）。
