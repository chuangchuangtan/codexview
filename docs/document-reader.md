# Generated report reader (6.3.0 development)

The published 6.2.1 release remains the stable baseline. The 6.3.0-dev.2 source is available on `main`; its implementation history is also preserved on `codex/document-reader`.

Last updated: 2026-10-21 (Asia/Shanghai).

Codex sessions often point to Markdown reports and HTML galleries saved on the server. Open these links in a separate browser tab while keeping the conversation available. Markdown supports headings, tables, code blocks and local report links. HTML uses an isolated, static preview; Read / Source and Refresh are available in the surrounding reader.

## Enable a project directory

On a build containing this feature:

```sh
codexview serve --host 0.0.0.0 --port 80 --file-root /path/to/project/reports
```

Use the session’s project working directory (`cwd`) when reports span several project subdirectories; do not point this option at the Codex session storage directory. Repeat `--file-root` for additional report directories. Stop an existing instance before changing its startup options. File reading is disabled when no roots are configured. A browser user can read supported files within the shared directories: choose narrow report folders, and use the same access protection as the session viewer.

Links such as `[Report](/path/to/project/reports/result.md)` and `[Gallery](/path/to/project/reports/index.html)` open the reader. Relative links in Native conversations use the `cwd` from the first session metadata record, read with a 64 KiB bound when the report is requested. Relative document and image links in Markdown reports resolve beside that report.

## Reading and navigation

Markdown reports have an optional Contents menu for up to 120 rendered headings, including Unicode and duplicate headings. Heading links take priority over saved positions. Unchanged Markdown reports restore the visible paragraph; a changed file skips stale coordinates. Session bookmarks restore a task and paragraph after hydration, including a saved payload page. A bare session URL resumes the saved task, explicit task links select that task, and the report return link requests resume. Bookmarks store short text anchors and positions only in browser localStorage, with limits of 100 sessions and 50 reports. They are specific to the browser and site origin. No transcript index or server write is added.

Task density and reading-width presets are available in More actions. Sidebar and content drag handles remain available.

## Boundaries

- No filesystem-wide browser, recursive scan, report index, background file monitoring or source writes.
- All path components are opened with directory descriptors and `O_NOFOLLOW`; symlinks, hidden paths, special files, paths outside configured roots and Codex-owned data are refused.
- Supported documents: UTF-8 `.md`, `.markdown`, `.html`, `.htm`.
- Local static resources: CSS, PNG, JPEG, GIF, WebP and ICO. Approved local Markdown/HTML links in HTML open the current file in the outer reader after a user click; filename, Source and Refresh all follow that file. Same-page anchors stay in the preview. The return link retains the originating session and task.
- HTML sanitization removes active elements and URL-bearing attributes except approved local report/resource references. Scripts, forms, embedded frames, external resources and network APIs are disabled by a response CSP and an iframe sandbox. Only user-activated top navigation is permitted so approved document links can reach the outer reader. Scripts and same-origin privileges remain disabled. Direct visits to the raw HTML endpoint also receive the restrictive sandbox CSP.
- JavaScript applications, interactive charts, inline SVG and external fonts/assets are not supported by static preview. The original source is available as escaped text.
- Preview limits: Markdown 2 MiB, HTML 4 MiB, CSS 1 MiB and each raster image 16 MiB. Oversize files produce an explicit error; contents are never silently truncated.
- Refresh reads saved content on demand. It does not follow unsaved editor buffers.

This implementation adds no third-party runtime dependencies and does not change session indexing or search algorithms.

Sandbox references: [MDN iframe](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe) and [CSP sandbox](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/sandbox).
