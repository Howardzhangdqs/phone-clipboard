# Changelog

本项目的所有显著变更都记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本 SemVer](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 计划中
- 可选的一次性访问令牌（查询参数鉴权）
- 电脑 → 手机方向的回传
- Docker 镜像

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
