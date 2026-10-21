# Security and privacy

CodexView is a personal, self-hosted transcript reader. Keep the default loopback bind and use SSH forwarding, or configure an authenticated reverse proxy. It does not provide accounts, access control between users, TLS, or a sandbox for arbitrary local attackers.

Codex-owned sessions, rollouts, configuration and authentication files are opened read-only. The app neither executes transcript commands nor drives the Codex TUI. All runtime state, manifests and logs belong to `$CODEX_HOME/codexview`. Review notes are private data, not a disposable cache.

Review requests reject external Origin headers and cross-site fetches. Request bodies are limited to 64 KiB. Stored review text is capped at 20,000 characters. Source text is escaped before HTML rendering. Responses send a same-origin connection policy, no-sniff header, frame protection and no-store. Inline scripts/styles are part of the single-file distribution; the CSP allows these intentionally.

Own-runtime atomic writes and writable file handles refuse symbolic-link redirection. This is not a defense against an attacker who already has write access to your user account or is racing directory replacements. Run only one server per runtime directory and restrict file permissions.

Search records can contain sensitive commands and output. No analytics, cloud processing, remote fonts or external script/CDN dependencies are included. Do not post real rollouts, notes, deployment records or screenshots in public issues. Use a minimal synthetic reproduction. Report security issues privately to the repository maintainer through the hosting platform's private reporting mechanism when available.
