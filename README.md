# CodexView

A lightweight, read-only viewer for Codex CLI sessions. Browse server conversations, search execution records, mark important tasks, and keep private review notes.

**Single-file deployment · Built with Python · No third-party runtime dependencies**

[中文说明](README.zh-CN.md) · [MIT License](LICENSE)

![CodexView session reader](docs/images/reader.png)

## Install

Supports Linux and macOS with Python 3.7 or newer. Use a maintained Python version for new installations. Windows has not been validated.

Download **[codexview-6.2.1](https://github.com/chuangchuangtan/codexview/releases/download/v6.2.1/codexview-6.2.1)**, open a terminal in the download directory, and run:

```sh
mkdir -p "$HOME/.local/bin"
cp codexview-6.2.1 "$HOME/.local/bin/codexview"
chmod +x "$HOME/.local/bin/codexview"
export PATH="$HOME/.local/bin:$PATH"
codexview --version
```

The final command should print `CodexView 6.2.1`.

**Keep PATH available in new terminals:** choose the commands for your shell. Run `echo "$SHELL"` if you are unsure.

Bash, commonly used on Linux servers:

```sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Zsh, the default shell on macOS:

```sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## Start and open

Run this **on the server or inside the container where Codex CLI runs**:

```sh
codexview serve --host 0.0.0.0 --port 80
```

The service runs in the background. Open the appropriate address in your browser:

| Deployment | Browser address |
| --- | --- |
| Server listening directly on port 80 | `http://SERVER_IP/` |
| Container port 80 mapped to host port 23680 | `http://HOST_IP:23680/` |

Configure port publishing in your container environment; CodexView does not create container mappings. Binding port 80 requires the appropriate permissions. You can choose another port when needed.

For **local access only**, run:

```sh
codexview serve
```

Then open **http://127.0.0.1:17864/**. This default listens only on the local machine; it differs from the server configuration above.

There is no built-in login. Use a trusted network, an authenticated reverse proxy, or SSH forwarding for remote access.

## Common commands

| Action | Command |
| --- | --- |
| Check service status | `codexview status` |
| Check the environment | `codexview doctor` |
| Follow server logs | `codexview logs --follow` |
| Stop the service | `codexview stop` |
| Show help | `codexview --help` |

If Codex uses a custom data directory:

```sh
codexview serve --host 0.0.0.0 --port 80 --codex-home /path/to/.codex
```

Directory priority: `--codex-home` → `CODEX_HOME` environment variable → `~/.codex`.

## Features

- **Large-session reading:** tasks load on demand; expand execution evidence when needed.
- **Search:** find sessions, filter task titles, and search content by role.
- **Navigation:** jump by task number, choose Latest, use J/K, or share a task link.
- **Time and evidence:** task start timestamps and paired tool calls/outputs.
- **Review:** Important, Marked, Later, Reviewed, and separate notes.
- **Reading comfort:** dark/light themes, font controls, resizable sidebar and content, mobile navigation.

Use Cmd/Ctrl F to search session content and `/` to filter task titles. Refresh checks appended records. Task timestamps use your browser's local timezone.

## Data safety and upgrades

Codex-owned sessions, rollouts, configuration and authentication files remain strictly read-only. Native session discovery stays enabled. CodexView neither controls Codex CLI nor executes commands found in conversations.

Review state, caches and logs are stored only under `$CODEX_HOME/codexview/`. Before upgrading, back up **`state/`**, stop the service, replace the program, and restart with the same options. Review notes are not disposable cache files.

This is a **public preview**. First-time search of very large files can take several seconds; results are limited to 200 matching records. Multi-user access control and complete coverage of every Codex record format are not provided.

## Other downloads

- [ZIP](https://github.com/chuangchuangtan/codexview/releases/download/v6.2.1/codexview-6.2.1.zip) / [tar.gz](https://github.com/chuangchuangtan/codexview/releases/download/v6.2.1/codexview-6.2.1.tar.gz): full source and documentation.
- [SHA256SUMS](https://github.com/chuangchuangtan/codexview/releases/download/v6.2.1/SHA256SUMS): SHA-256 checksums for release assets.

Released under the [MIT License](LICENSE). See [Security](SECURITY.md) and [Contributing](CONTRIBUTING.md) for more information.

CodexView is an independent project, not affiliated with or supported by OpenAI. Documentation screenshots contain synthetic conversations only.
