# CodexView

轻量、只读的 Codex CLI 会话阅读器。在浏览器中查看服务器会话、搜索执行记录、标记重点并保存审阅笔记。

**单文件部署 · Python 实现 · 无需安装第三方依赖**

[English](README.md) · [MIT 许可证](LICENSE)

![CodexView 会话阅读界面](docs/images/reader.png)

## 安装

支持 Linux 和 macOS，需要 Python 3.7 或更新版本。推荐使用仍受维护的 Python。Windows 暂未验证。

下载发布文件 **`codexview-6.2.1`**，在下载目录打开终端，依次执行：

```sh
mkdir -p "$HOME/.local/bin"
cp codexview-6.2.1 "$HOME/.local/bin/codexview"
chmod +x "$HOME/.local/bin/codexview"
export PATH="$HOME/.local/bin:$PATH"
codexview --version
```

最后显示 `CodexView 6.2.1` 即表示安装成功。

**将 PATH 永久保存：**根据使用的终端选择一组命令。可运行 `echo "$SHELL"` 查看当前终端类型。

Bash（常见 Linux 服务器）：

```sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Zsh（macOS 默认终端）：

```sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## 启动与访问

在**运行 Codex CLI 的服务器或容器内**执行：

```sh
codexview serve --host 0.0.0.0 --port 80
```

服务默认在后台运行，随后在浏览器访问服务器地址。

| 部署方式 | 浏览器访问地址 |
| --- | --- |
| 服务器直接监听 80 | `http://服务器IP/` |
| 容器内 80 映射到宿主机 23680 | `http://宿主机IP:23680/` |

容器端口映射需在容器环境中配置，CodexView 不会自动创建映射。80 端口需要相应绑定权限，普通用户也可选用其他端口。

**仅在本机查看**时，可以直接运行：

```sh
codexview serve
```

然后打开 **http://127.0.0.1:17864/**。这是默认配置，只允许本机访问，与上面的服务器部署方式不同。

工具不内置登录认证。请在可信网络内使用；需要公网访问时，请配置认证反向代理，或使用 SSH 转发。

## 常用操作

| 操作 | 命令 |
| --- | --- |
| 查看运行状态 | `codexview status` |
| 检查运行环境 | `codexview doctor` |
| 实时查看日志 | `codexview logs --follow` |
| 停止服务 | `codexview stop` |
| 查看帮助 | `codexview --help` |

Codex 数据不在默认目录时，指定实际位置：

```sh
codexview serve --host 0.0.0.0 --port 80 --codex-home /path/to/.codex
```

目录优先级：`--codex-home` → `CODEX_HOME` 环境变量 → `~/.codex`。

## 功能

- **快速阅读大会话**：任务按需加载，执行活动展开后读取。
- **查找内容**：检索会话、筛选任务标题，按角色搜索正文。
- **快速定位**：任务号直达、Latest、J/K 前后切换、任务链接。
- **时间与证据**：显示任务开始时间，合并展示工具调用和输出。
- **审阅记录**：Important、Marked、Later、Reviewed 与独立笔记。
- **舒适阅读**：明暗主题、字体调整、可拉伸侧栏与正文宽度、手机导航。

Cmd/Ctrl F 搜索会话内容，`/` 筛选任务标题。点击 Refresh 检查新追加的记录。任务时间按浏览器本地时区显示。

## 数据安全与升级

Codex 原始 session、rollout、config、auth 数据严格只读，Native 会话发现始终开启。工具不操控 Codex CLI，也不运行会话中出现的命令。

审阅状态、缓存和日志仅保存在 `$CODEX_HOME/codexview/`。升级前请备份其中的 **`state/`** 目录，停止服务、替换程序，再使用原参数启动。不要删除审阅笔记来清理缓存。

当前为**公开预览版**。首次搜索超大文件可能需要数秒；搜索最多返回 200 条匹配记录。暂不提供多用户权限管理，尚未覆盖所有 Codex 记录格式。

## 其他下载

- `codexview-6.2.1.zip` / `.tar.gz`：完整源码和文档。
- `SHA256SUMS`：发布文件的 SHA-256 校验值。

采用 [MIT License](LICENSE)。更多信息：[安全说明](SECURITY.md) · [参与贡献](CONTRIBUTING.md)。

CodexView 是独立项目，与 OpenAI 无隶属或官方支持关系。文档截图仅使用虚构会话。
