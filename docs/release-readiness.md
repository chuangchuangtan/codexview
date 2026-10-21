# 6.2.1 public-preview readiness

Assessment date: 2026-10-21. This is an initial public-preview release, not a claim of production-grade multi-user hosting or full Codex CLI schema compatibility.

| Area | Release evidence | Limits |
| --- | --- | --- |
| Runtime footprint | Single embedded executable, Python standard library only | Linux/macOS; Windows not validated |
| Source boundary | Read-only source handles; separate own-runtime writes; corrupt-state and redirection tests | Trusted personal environment; no account-level sandbox |
| Core behavior | Synthetic tests for discovery, appends, partial records, source replacement, task pairing, search, pagination and timestamps | Record-family coverage is not exhaustive |
| UI | DOM tests plus desktop/mobile browser verification; task list area and timestamps checked | No automated full-browser CI across all engines |
| Large sessions | Real approximately 600 MB session exercised; cold manifest and warm/search times recorded privately | First search and exceptional JSON records remain expensive |
| Packaging | Repeated builds produce identical executable/archive hashes in the tested toolchain; neutral tar metadata and fixed ZIP/gzip timestamps | Compression bytes can depend on the Python/zlib toolchain |
| Privacy | Public allowlist, clean upload tree, synthetic README screenshot | Maintainers must continue reviewing new public inputs |
| Documentation | English and Chinese README, architecture, security, contributor and performance notes | UI currently English |
| License | MIT in root LICENSE; development dependencies not bundled | Project is independent of OpenAI |
| CI | GitHub Actions definitions included; local commands exercised | See the latest GitHub Actions run for hosted validation |

## Release assets

- `codexview-6.2.1`: standalone program.
- `codexview-6.2.1.tar.gz` and `codexview-6.2.1.zip`: full public source trees.
- `codexview-6.2.1.manifest.json`: per-source SHA-256 manifest.
- `SHA256SUMS`: checksums of downloadable assets.
- `dist/codexview-6.2.1-source/`: clean directory suitable for initializing a public repository.

The parent development workspace contains historical/private files. Publish only the clean tree or reviewed release assets. Existing deployment files, real rollouts, notes and private acceptance screenshots are intentionally absent.

## Before publishing on GitHub

1. Choose the repository owner/name and initialize Git from the clean tree, not its parent workspace.
2. Push the source and run the included GitHub Actions. Investigate failures before tagging a release.
3. Create the `v6.2.1` tag and mark the GitHub Release as a **pre-release / public preview**.
4. Attach the standalone program, source archives, source manifest and checksums produced together.
5. Enable a private security-reporting route and review issue attachments for sensitive session data.

The local packaging tool does not upload files. Pushing a version tag triggers the included Release workflow, which builds the reviewed source and publishes preview assets.
