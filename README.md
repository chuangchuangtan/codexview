<div align="center">
  <h1>CodexView</h1>
  <p><strong>Thousands of turns. Clear context.</strong></p>
  <p>Keep the work running in your terminal. Read, search and navigate in your browser.</p>
  <p><code>1,000+ turns</code> · <code>On-demand loading</code> · <code>Single file</code> · <code>Read-only</code></p>
  <p><a href="https://github.com/chuangchuangtan/codexview/releases/tag/v6.3.0-dev.5">Download</a> · <a href="README.zh-CN.md">中文说明</a> · <a href="LICENSE">MIT License</a></p>
</div>

CodexView is a lightweight Codex CLI reader built for **hundreds to thousands of conversation turns**. Browse conversations, tool execution and Markdown / HTML reports from your machine or a remote server, find earlier decisions in context, and continue where you stopped reading.

| **Long sessions, readable by task** | **Find records in context** | **Small deployment, read-only sources** |
| --- | --- | --- |
| Navigate thousands of turns; load content on demand and jump by task number | Content search, task timestamps, reading recovery and report viewing | One file, Python standard library, no third-party runtime dependencies |

**Scale validation**: a 2,000-turn synthetic session and a 755-task, approximately 616 MB real session have been exercised separately, covering task count and large-file workloads. [See validation scope and performance records](docs/performance.md#task-count-validation-2026-10-21).

**Last updated: 2026-10-25 (Asia/Shanghai)** · Current version: `6.3.0-dev.5` · Development preview

![CodexView at turn 1,000 of a 2,000-turn synthetic session](docs/images/continuous-reader.png)

## Why CodexView

| When you need to… | CodexView helps you… |
| --- | --- |
| Read a conversation that has outgrown terminal scrollback | Browse a task navigator, jump by task number, and see task start times |
| Find an earlier error, decision, or discussion about a file | Search session content and jump back to the matching context |
| Read replies buried in tool output | Use Reading focus; expand execution details when needed |
| Check recent progress while a long task continues | See new-content notifications; explicitly Follow latest, or refresh when ready |
| Return to a project the next day | Filter sessions and task titles; keep important tasks and separate notes |
| Read work running on a remote server | Deploy beside Codex CLI and open the reader in your browser |

![How Codex CLI execution and CodexView read-only browsing work together](docs/images/scenarios-en.png)

### One Codex instance runs the session. Read it without starting another.

Keep one Codex CLI instance responsible for executing a session. Reading its history should not require starting another Codex instance, resuming the same session, or interrupting the work. CodexView reads session records already written to disk without taking over the active session. The original Codex instance can keep working; check new-content notifications or explicitly Follow latest.

Browser reading is independent of the Codex CLI execution instance. CodexView does not enable multiple Codex instances to operate on the same session, and it never executes commands found in conversation text.

## Install

Install **6.3.0-dev.5 (development preview)**, including continuous reading and Markdown / static HTML reports.

When upgrading, run `codexview stop` and back up review state before replacing the program.

Supports Linux and macOS with Python 3.7 or newer. Use a maintained Python version for new installations. Windows has not been validated.

Download **[codexview-6.3.0-dev.5](https://github.com/chuangchuangtan/codexview/releases/download/v6.3.0-dev.5/codexview-6.3.0-dev.5)**, open a terminal in the download directory, and run:

```sh
mkdir -p "$HOME/.local/bin"
cp codexview-6.3.0-dev.5 "$HOME/.local/bin/codexview"
chmod +x "$HOME/.local/bin/codexview"
export PATH="$HOME/.local/bin:$PATH"
codexview --version
```

The final command should print `CodexView 6.3.0-dev.5`.

Previous baseline: [6.2.1](https://github.com/chuangchuangtan/codexview/releases/tag/v6.2.1). Use each Release’s own files and feature list.

**Keep PATH available in new terminals**: choose the commands for your shell. Run `echo "$SHELL"` if you are unsure.

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

Then open **[http://127.0.0.1:17864/](http://127.0.0.1:17864/)**. This default listens only on the local machine; it differs from the server configuration above.

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

## 2026-10-21 update: continuous reading (6.3.0-dev.5)

**2026-10-25 · 6.3.0-dev.5 hotfix:** prevents duplicate task mounting and stabilizes forward/backward scrolling. Passive scrolling updates task selection without restarting the reader; measured task heights are retained during restoration. Review saves and task navigation from the preceding hotfix are retained.

The preview also includes:

- **Continuous scrolling:** keep the height of evicted tasks and preload adjacent content; no delayed snap back after loading. Exceptional tasks use section chunks while retaining search and reading positions.
- **Live progress:** a new-content indicator checks file metadata while the page is visible. Follow latest is explicit; manual reading pauses it.
- **Task context:** a compact sticky title and timestamp stay visible above a long answer.
- **Optional faster search:** choose **Search → Build search cache**. A compressed sidecar preserves Chinese substring matching, updates appended text when requested, supports cancellation and falls back to streaming. It never builds during session entry.
- **Reports and images:** collect report links as you read; inspect local images with zoom and return to the originating report. Related sessions use explicit parent/fork metadata only.

Includes the existing Markdown/static HTML reader, Read / Source, heading contents, paragraph recovery and adjustable layout. Reports load only when opened inside configured project roots.

After installing **6.3.0-dev.5**, enable a project directory for report reading:

```sh
codexview serve --host 0.0.0.0 --port 80 --file-root /path/to/project/reports
```

Set `--file-root` to the server project working directory (the session’s `cwd`), such as `/path/to/project`, rather than `.codex/sessions`. Repeat it for additional directories. Stop an existing instance before changing startup options. File reading is disabled by default. HTML scripts, forms and external resources are disabled; JavaScript-dependent applications are not supported.

**Published 6.2.1 assets remain unchanged**, with the additional `stable-6.2.1-20261021` baseline tag. See [report reader setup and limits](docs/document-reader.md), [stable baseline](docs/baselines/6.2.1.md) and [changelog](CHANGELOG.md).

## Data safety and upgrades

Codex-owned sessions, rollouts, configuration and authentication files remain strictly read-only. Native session discovery stays enabled. CodexView neither controls Codex CLI nor executes commands found in conversations.

Review state, caches and logs are stored only under `$CODEX_HOME/codexview/`. Before upgrading, back up **`state/`**, stop the service, replace the program, and restart with the same options. Review notes are not disposable cache files.

Search caches contain readable session text and stay under the same protected runtime directory. Each is limited to 128 MiB; two ready caches are retained, with one additional temporary build. See [reading controls and limits](docs/continuous-reading.md).

This is a **public preview**. First-time search of very large files can take several seconds; results are limited to 200 matching records. Multi-user access control and complete coverage of every Codex record format are not provided.

## Other downloads

Earlier versions: [6.3.0-dev.4](https://github.com/chuangchuangtan/codexview/releases/tag/v6.3.0-dev.4) (review controls) · [6.3.0-dev.3](https://github.com/chuangchuangtan/codexview/releases/tag/v6.3.0-dev.3) (continuous reading) · [6.3.0-dev.2](https://github.com/chuangchuangtan/codexview/releases/tag/v6.3.0-dev.2) (reading refinement) · [6.3.0-dev](https://github.com/chuangchuangtan/codexview/releases/tag/v6.3.0-dev) (first report-reader preview) · [6.2.1](https://github.com/chuangchuangtan/codexview/releases/tag/v6.2.1) (previous baseline).

- [ZIP](https://github.com/chuangchuangtan/codexview/releases/download/v6.3.0-dev.5/codexview-6.3.0-dev.5.zip) / [tar.gz](https://github.com/chuangchuangtan/codexview/releases/download/v6.3.0-dev.5/codexview-6.3.0-dev.5.tar.gz): full source and documentation.
- [SHA256SUMS](https://github.com/chuangchuangtan/codexview/releases/download/v6.3.0-dev.5/SHA256SUMS): SHA-256 checksums for release assets.

Released under the [MIT License](LICENSE). See [Security](SECURITY.md) and [Contributing](CONTRIBUTING.md) for more information.

CodexView is an independent project, not affiliated with or supported by OpenAI. Documentation screenshots contain synthetic conversations only; scenario diagrams illustrate the reading workflow.
