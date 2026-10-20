# 贡献指南

感谢你愿意为 phone-clipboard 贡献！

## 开发原则

本项目刻意保持**单文件、零第三方依赖**（`server.py` 仅用 Python 标准库）。
提交请遵守这一边界：

- 运行时不得引入任何 `import` 第三方库；增强能力一律做成"存在则用、不存在则优雅回退"（参考 `qrcode`、`pyperclip` 的处理方式）。
- `_clip_writer.py` 仅依赖系统 GTK4（`gi`），且必须保持失败即退（退出码 2/3）的契约，供 `server.py` 回退决策。
- 保持对无图形环境（SSH 无头会话）的兼容：GTK4 不可用时功能仍可用（走 CLI 后端）。

## 工作流程

1. Fork 并从 `main` 拉取特性分支：`git checkout -b feat/xxx`。
2. 保证 `python3 -m py_compile server.py _clip_writer.py` 通过；有逻辑改动时请同步更新：
   - `README.md`（用户可见行为）
   - `CHANGELOG.md`（`[Unreleased]` 一节）
3. 提交信息使用 conventional commits 风格：`feat:` / `fix:` / `docs:` / `chore:`。
4. 发起 Pull Request，描述清楚动机与测试方式。

## 代码风格

- Python 遵循 PEP 8；本项目为中文注释友好型，注释请解释"为什么"而非复述代码。
- 网页端为内嵌单文件 HTML/CSS/JS，不引入构建工具链。
- 运行 `bash -n start.sh` 校验 shell 脚本语法。

## 安全相关

任何涉及鉴权、网络暴露面、剪贴板内容的改动，请在 PR 中显著说明，并同步更新
[SECURITY.md](SECURITY.md) 的威胁模型一节。
