#!/usr/bin/env python3
"""
带 x-kde-passwordManagerHint 的剪贴板写入器（GTK4，强制 X11 后端）。

用法: printf '文本' | python3 _clip_writer.py
原理: 通过 Gdk.ContentProvider.new_union 同时提供正常文本目标和
      x-kde-passwordManagerHint（密码管理器标准提示）。
      粘贴完全正常，但遵循该提示的剪贴板历史工具
      （Copyous 的 MimeTypes.Sensitive、Klipper 等）不会将其写入历史。
说明: 无头进程在 Wayland 下的 set_selection 会被 mutter 的 serial 校验拒绝，
      因此强制 X11(XWayland) 后端——与 xclip 同机制，已实测 Copyous 不记录。
退出码: 0=所有权移交/超时后正常退出  2=设置剪贴板失败  3=环境不可用(GTK4/显示缺失)
"""
import os
import sys

os.environ['GDK_BACKEND'] = 'x11'  # 必须在打开显示前设置; 无头 Wayland 会被 mutter 拒绝

try:
    from gi import require_version
    require_version('Gtk', '4.0')
    require_version('Gdk', '4.0')
    require_version('GLib', '2.0')
    from gi.repository import Gdk, GLib, Gtk
except Exception:
    sys.exit(3)

try:
    _ok = Gtk.init_check()
    if isinstance(_ok, tuple):
        _ok = _ok[0]
    if not _ok:
        sys.exit(3)
except Exception:
    sys.exit(3)

DATA = sys.stdin.buffer.read()
TEXT_MIMES = ('text/plain;charset=utf-8', 'text/plain', 'UTF8_STRING')
HINT_MIME = 'x-kde-passwordManagerHint'

display = Gdk.Display.get_default()
if display is None:
    sys.exit(3)

providers = [Gdk.ContentProvider.new_for_bytes(m, GLib.Bytes.new(DATA)) for m in TEXT_MIMES]
providers.append(Gdk.ContentProvider.new_for_bytes(HINT_MIME, GLib.Bytes.new(b'')))

clipboard = display.get_clipboard()
if not clipboard.set_content(Gdk.ContentProvider.new_union(providers)):
    sys.exit(2)

loop = GLib.MainLoop.new(None, False)


def _quit(*_args):
    loop.quit()
    return False


# 1 小时兜底退出，避免进程无限驻留
GLib.timeout_add(3600 * 1000, _quit)


# 0.5 秒后监听剪贴板易主（他人写入）事件，届时退出——同 xclip 行为，不堆积进程
def _watch():
    clipboard.connect('changed', _quit)
    return False


GLib.timeout_add(500, _watch)
loop.run()
