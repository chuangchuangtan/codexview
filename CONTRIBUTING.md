# Contributing

Keep runtime dependencies at zero. Edit `src/`, rebuild with `python3 tools/build.py`, and include the generated `codexview` executable. Preserve historical task IDs and review state unless a migration and fixtures demonstrate safety.

Run the Python, pure JavaScript and jsdom suites listed in README. Behavioral changes need representative synthetic fixtures. For performance changes, report a before/after with the same source, source size, record size distribution, runtime and cold/warm distinction. Do not substitute endpoint latency for browser rendering measurements.

Native discovery must stay enabled. Never write Codex-owned data, auto-run transcript content, add a CLI/TUI control bridge or eagerly parse the entire session on entry. Keep all derived state within CodexView's runtime tree. Public examples and screenshots must use synthetic data.

CI checks the generated artifact is current. Release packaging uses an allowlist; review its contents before publishing. This workspace may contain private historical artifacts that are intentionally excluded from Git and release archives.


## Build and test

Development requires Python and Node.js 22.22.2 or newer. The runtime itself uses only the Python standard library.

```sh
python3 tools/build.py
python3 -m unittest discover -s tests -v
npm ci
npm test
python3 tools/package_release.py
```

To inspect the UI without private data, run `python3 tools/demo.py` and open http://127.0.0.1:17866. Ctrl C stops the disposable demo. It never reads your actual Codex home.

The standalone release asset is named `codexview-6.2.1` without an extension. Install it as `codexview`. Complete archives contain the `codexview-6.2.1-source/` directory.
