#!/usr/bin/env python3
"""
手机 → 电脑剪贴板（单文件、零依赖，仅用 Python 标准库）

用法:
    python3 server.py            # 默认端口 8686
    python3 server.py -p 9090    # 换端口

手机和电脑连同一 Wi-Fi，用手机浏览器打开启动时打印的局域网地址即可。
页面包含: 输入框 / 连接状态按钮 / 清空按钮；输入停顿 1 秒后自动推送到电脑剪贴板。

电脑端剪贴板通道（自动探测）:
  首选 _clip_writer.py (GTK4): 附带 x-kde-passwordManagerHint 提示，
      Copyous / Klipper 等剪贴板历史工具不记录这些写入（粘贴不受影响）；
  回退: wl-copy(Wayland) / xclip / xsel(X11) / pbcopy(macOS) / pyperclip。
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, interactive-widget=resizes-content">
<title>手机 → 电脑剪贴板</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  html, body { height: 100%; }
  body {
    margin: 0; overflow: hidden;
    background: #101319; color: #e8eaf0;
    font-family: -apple-system, "PingFang SC", "HarmonyOS Sans SC", "Noto Sans SC", sans-serif;
  }
  /* 高度跟随"可视视口": 键盘弹出时页面随之收缩，保持各部分完整可见 */
  #app {
    height: var(--vvh, 100dvh);
    transform: translateY(var(--vvot, 0px));
    display: flex; flex-direction: column;
    justify-content: center;
    justify-content: safe center;
    gap: 14px;
    padding: 24px 20px calc(24px + env(safe-area-inset-bottom));
    overflow-y: auto;
    transition: height .25s ease, transform .25s ease;
  }
  header { display: flex; align-items: center; justify-content: space-between; }
  header h1 { margin: 0; font-size: 15px; font-weight: 600; color: #8b93a7; letter-spacing: .04em; }
  #toast { font-size: 12px; color: #6ee7a0; min-height: 16px; text-align: right; }
  textarea {
    width: 100%; flex: 1; min-height: 72px; padding: 14px 16px; font-size: 16px; line-height: 1.6;
    color: #e8eaf0; background: #191e27; border: 1px solid #262d3a; border-radius: 14px;
    outline: none; resize: vertical; caret-color: #5b9dff;
  }
  textarea:focus { border-color: #3d6fd6; box-shadow: 0 0 0 3px rgba(61,111,214,.15); }
  .row { display: flex; gap: 12px; }
  button {
    flex: 1; padding: 15px 0; font-size: 16px; font-weight: 600;
    border: none; border-radius: 14px; cursor: pointer; user-select: none;
    background: #191e27; border: 1px solid #262d3a; color: #e8eaf0;
  }
  button:active { transform: scale(.98); }
  #status { color: #ff7a7a; }
  #status.ok { color: #58d68d; border-color: #2c5c40; }
  footer { text-align: center; font-size: 12px; color: #59617a; }
</style>
</head>
<body>
<div id="app">
  <header>
    <h1>手机 → 电脑剪贴板</h1>
    <div id="toast"></div>
  </header>
  <textarea id="text" placeholder="在这里输入，停顿 1 秒后自动复制到电脑"
            autocomplete="off" autocapitalize="off" spellcheck="false"></textarea>
  <div class="row">
    <button id="status">连接中…</button>
    <button id="clear">清空</button>
  </div>
  <footer>与电脑连同一 Wi-Fi · 输入停顿 1 秒自动推送 · 失焦立即推送</footer>
</div>
<script>
  const $ = id => document.getElementById(id);
  const input = $('text'), statusBtn = $('status'), toast = $('toast');
  let toastTimer = null;

  function showToast(msg, ok = true) {
    toast.textContent = msg;
    toast.style.color = ok ? '#6ee7a0' : '#ff7a7a';
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toast.textContent = ''; }, 2500);
  }

  // 可视视口自适应: 键盘弹出/收起、旋转、缩放时，整页收缩到可见区域
  const vv = window.visualViewport;
  function fit() {
    const s = document.documentElement.style;
    s.setProperty('--vvh', vv.height + 'px');
    s.setProperty('--vvot', vv.offsetTop + 'px');
  }
  if (vv) {
    fit();
    vv.addEventListener('resize', fit);
    vv.addEventListener('scroll', fit);
  }

  // 连接状态: 打开时 + 每 3 秒自动检测，点击按钮可手动刷新
  async function ping() {
    try {
      const r = await fetch('/api/ping', { cache: 'no-store' });
      if (!r.ok) throw 0;
      statusBtn.textContent = '● 已连接';
      statusBtn.classList.add('ok');
    } catch {
      statusBtn.textContent = '● 未连接';
      statusBtn.classList.remove('ok');
    }
  }
  statusBtn.onclick = ping;
  ping();
  setInterval(ping, 3000);

  // 推送: 1 秒防抖；失焦立即推送，保证切换到电脑粘贴前已就绪
  let timer = null, last = null;
  function push() {
    const text = input.value;
    if (!text || text === last) return;  // 空内容不推送
    last = text;
    fetch('/api/copy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    })
      .then(r => r.json())
      .then(d => {
        if (d.ok) showToast('✓ 已复制到电脑');
        else showToast('复制失败: ' + (d.error || '未知错误'), false);
      })
      .catch(() => {});
  }
  input.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(push, 1000);
  });
  input.addEventListener('blur', () => { clearTimeout(timer); push(); });

  // 清空: 只清输入框本身，不推送空内容（电脑剪贴板保持不变）
  $('clear').onclick = () => {
    input.value = '';
    clearTimeout(timer);
    last = null;
    showToast('已清空');
    input.focus();
  };
</script>
</body>
</html>
"""

CLIP_CMDS = [
    ["wl-copy"],                           # Wayland
    ["xclip", "-selection", "clipboard"],  # X11
    ["xsel", "--clipboard", "--input"],    # X11
    ["pbcopy"],                            # macOS
]
TOOL = next((c for c in CLIP_CMDS if shutil.which(c[0])), None)

WRITER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_clip_writer.py")


def writer_available():
    """GTK4 写入器是否可用（写剪贴板时附带你 x-kde-passwordManagerHint，历史工具不记录）。"""
    if not os.path.exists(WRITER) or not os.environ.get("DISPLAY"):
        return False
    try:
        r = subprocess.run(
            [sys.executable, "-c",
             "from gi import require_version; require_version('Gtk', '4.0')"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


WRITER_OK = writer_available()


def set_clipboard_gtk(text):
    """优先通道: 经 _clip_writer.py 写入，剪贴板历史工具不记录。"""
    try:
        p = subprocess.Popen([sys.executable, WRITER], stdin=subprocess.PIPE,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p.stdin.write(text.encode("utf-8"))
        p.stdin.close()
        time.sleep(0.35)  # 成功则常驻持有所有权不退出；失败会立刻退出
        rc = p.poll()
        if rc is None or rc == 0:
            return True, "gtk+免历史", ""
        return False, "gtk", f"writer rc={rc}"
    except Exception as e:
        return False, "gtk", str(e)


def set_clipboard(text: str):
    """把文本写入系统剪贴板，返回 (ok, tool, error)。"""
    if WRITER_OK:
        ok, tool, err = set_clipboard_gtk(text)
        if ok:
            return ok, tool, err
    if TOOL:
        try:
            p = subprocess.Popen(TOOL, stdin=subprocess.PIPE,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            p.communicate(text.encode("utf-8"), timeout=5)
            return True, TOOL[0], ""
        except subprocess.TimeoutExpired:
            p.kill()
            return True, TOOL[0], "(写入超时，内容通常已生效)"
        except Exception as e:
            return False, TOOL[0], str(e)
    try:  # 回退: pyperclip
        import pyperclip
        pyperclip.copy(text)
        return True, "pyperclip", ""
    except Exception:
        return False, "", "未找到剪贴板后端，请安装 xclip / wl-clipboard / pyperclip 之一"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, HTML, "text/html; charset=utf-8")
        elif self.path == "/api/ping":
            self._send(200, json.dumps(
                {"ok": True, "tool": (TOOL[0] if TOOL else "pyperclip?")}, ensure_ascii=False))
        else:
            self._send(404, json.dumps({"ok": False, "error": "not found"}, ensure_ascii=False))

    def do_POST(self):
        if self.path != "/api/copy":
            self._send(404, json.dumps({"ok": False, "error": "not found"}, ensure_ascii=False))
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n > 10 * 1024 * 1024:
                self.close_connection = True
                return self._send(413, json.dumps({"ok": False, "error": "too large"}))
            payload = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
            text = payload.get("text", "")
            if not isinstance(text, str):
                raise ValueError("text must be a string")
        except Exception as e:
            return self._send(400, json.dumps(
                {"ok": False, "error": f"bad request: {e}"}, ensure_ascii=False))
        if text == "":  # 空内容: 不动剪贴板（前端已拦截，这里兜底）
            ok, tool, err = True, (TOOL[0] if TOOL else "?"), "(空内容，跳过复制)"
        else:
            ok, tool, err = set_clipboard(text)
        self._send(200, json.dumps({"ok": ok, "tool": tool, "error": err}, ensure_ascii=False))
        print(f"[{datetime.now():%H:%M:%S}] {'✓' if ok else '✗'} 复制 {len(text)} 字符 "
              f"-> {tool or '?'} {err}".rstrip())
        sys.stdout.flush()

    def log_message(self, *args):  # 关闭默认访问日志，只保留复制记录
        pass

    # 空闲 keep-alive 连接 30 秒后由服务端主动关闭，
    # 避免线程一直阻塞在 readline() 里等手机浏览器的下一个请求
    timeout = 30


class QuietServer(ThreadingHTTPServer):
    """手机浏览器锁屏/切后台/关页面时会直接 RST 掉 keep-alive 连接，
    标准库默认会为每个被重置的连接打印整段 traceback（无害但很吵）。
    这里把这类"对端断开"异常静默掉，其余异常仍走默认处理。"""

    def handle_error(self, request, client_address):
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, ConnectionAbortedError,
                            BrokenPipeError)):
            return
        super().handle_error(request, client_address)


def lan_ips():
    ips = set()
    try:  # 不实际发包，仅让内核选路由拿本机出口 IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("223.5.5.5", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith(("127.", "169.254.")):
                ips.add(ip)
    except OSError:
        pass
    return sorted(ips)


def main():
    ap = argparse.ArgumentParser(description="手机输入 → 电脑剪贴板")
    ap.add_argument("-p", "--port", type=int, default=8686)
    ap.add_argument("-b", "--bind", default="0.0.0.0")
    args = ap.parse_args()

    if TOOL is None and not WRITER_OK:
        print("⚠ 未检测到 wl-copy / xclip / xsel / pbcopy / GTK4，复制可能失败；"
              "安装任一即可: sudo apt install xclip 或 wl-clipboard")

    try:
        srv = QuietServer((args.bind, args.port), Handler)
    except OSError as e:
        sys.exit(f"启动失败: {e}（端口被占用？换个端口试试: python3 server.py -p 9090）")

    ips = lan_ips()
    print("═" * 46)
    print("  手机 → 电脑剪贴板  已启动")
    backend = "gtk4+免历史提示" if WRITER_OK else (TOOL[0] if TOOL else "pyperclip(未确认)")
    print(f"  剪贴板后端: {backend}"
          + ("" if WRITER_OK else "  (会进入剪贴板历史)"))
    print("  手机连同一 Wi-Fi，用手机浏览器打开:")
    for ip in ips:
        url = f"http://{ip}:{args.port}"
        print(f"    {url}")
        try:  # 装了 qrcode 库就在终端直接显示二维码（可选）
            import qrcode
            qr = qrcode.QRCode(border=1)
            qr.add_data(url)
            qr.print_ascii(invert=True)
            break
        except ImportError:
            pass
    if not ips:
        print(f"    http://<电脑局域网IP>:{args.port}  (未能自动获取本机 IP，用 ip addr 查看)")
    print("  Ctrl+C 停止")
    print("═" * 46)
    sys.stdout.flush()

    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
