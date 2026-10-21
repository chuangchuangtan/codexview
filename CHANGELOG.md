# Changelog

## 6.3.0-dev.2 — 2026-10-21 (Asia/Shanghai) — reading refinement

- Restore per-session task and paragraph positions using bounded browser-local bookmarks; honor explicit task links and invalidate stale section positions.
- Keep HTML navigation, filename, source and refresh on the same current report, with a return link to the originating task.
- Add an optional Markdown heading outline with Unicode and duplicate-heading anchors.
- Add compact task rows, reading-width presets and grouped review controls without changing task virtualization or search.
- Retain the 6.2.1 stable release and the preceding 6.3.0-dev source baseline.
- Publish versioned standalone/source preview packages for 6.3.0-dev and 6.3.0-dev.2, with matching English/Chinese installation links and release-time version checks.

## 6.3.0-dev — 2026-10-21 (Asia/Shanghai) — generated report reader

- Preserve 6.2.1 with a stable baseline tag and rollback record.
- Open linked Markdown and static HTML reports in an independent reader, on demand.
- Add explicit read-only project roots, bounded file reads, isolated HTML, local raster/CSS resources, source view and manual refresh.
- Keep Native discovery, session indexes, virtual reading and search algorithms unchanged.


## 6.2.1

- Compress task navigator controls into three rows; leave the remaining sidebar height to the task list.
- Move review progress to an overview button and replace the six-button filter panel with a compact selector.
- Display each Native task's original start timestamp in the browser's local timezone, loaded with task metadata without rebuilding the manifest.

## 6.2.0

- Establish canonical Python/web sources and a reproducible, standalone build.
- Redesign session library and reading colors, typography and spacing; add source filtering and sorting.
- Add task-number navigation, Latest action, accessible task rows and mobile drawer.
- Synchronize virtual navigator with explicit task navigation; preserve reading position when earlier task prose hydrates.
- Locate search hits beyond the first payload page; add keyboard result selection, escaped snippet highlighting and stale-request protection.
- Cache up to 12 recent search results, invalidated on source changes.
- Remove superseded synchronous Native index implementation and unavailable export action.
- Improve retry behavior, clipboard error reporting, saved-state error handling and source preparation status.
- Add response security headers, cross-origin write rejection, bounded request bodies and own-runtime file redirection checks.
- Add open-source documentation, CI definitions and allowlisted release packaging. Keep Native discovery and existing review identity.
