# Performance acceptance and next iterations

Do not report HTTP response time as browser paint time. Measure cold manifest, warm manifest, task structure, first readable task, first search and cached search separately. Keep source size, largest record, task count, Python version and sample count with results.

## Release gates

| Stage | Gate | Verification |
|---|---|---|
| Discovery | Native remains enabled; library metadata p95 <250 ms for 1,000 local entries on the target host | Fixed-depth fixture / real directory; no transcript read |
| Shell | HTTP p95 <300 ms for a 600 MiB session; no manifest scan in request | 5+ samples, cold and warm |
| Manifest | Warm <250 ms; cold <8 s for the target 600 MiB file | Separate isolated runtime; source unchanged |
| Task | HTTP p95 <300 ms for representative target tasks | Structures and selected payload measured separately |
| Reader | At most 3 task DOM nodes; no unintended navigation on resize or background hydration | Browser and DOM integration |
| Search | First <10 s for target 600 MiB file; repeat <250 ms warm | Same semantic query, unchanged source; cancel exercised |
| Navigation | Visible search hit and matching sidebar item; direct task and Latest work | Real browser, desktop and 390 px width |
| Layout | No horizontal page overflow at 390 px; resize handles work with mouse and keyboard | Real browser |
| Safety | Source content hash unchanged; no external-origin state write; corrupt notes preserved | Temporary fixtures plus target file stat/hash |

These are acceptance targets, not universal guarantees or completed 1,000-session benchmarks. A large single task, slow storage, shared server contention or very large record can exceed them. Current real-host acceptance is kept privately outside the open-source release archive.

## Remaining work in priority order

1. **Representative fixtures and repeatable browser benchmark.** Add multiple supported CLI schema versions, tool families, empty sessions, long Unicode output and synthetic large sessions. Separate first visible text from full task hydration, and include keyboard/mobile acceptance.
2. **Precise incremental updates.** Stat-based freshness notifications, an explicit follow-latest switch, no unsolicited scroll changes. Maintain task and review identity across appends/restarts.
3. **Optional incremental search index.** Benchmark SQLite FTS or compact sidecar postings against sequential scan. Build in the background, bound disk and memory, index only readable text, support cancellation, and never put index building on session entry.
4. **Turn-aware adapter and subagent navigation.** Migration fixtures must prove stable review mapping. Never silently reinterpret old task IDs.
5. **Large-task virtualization.** The current bound is tasks, not section nodes inside one exceptional task. Add section-window rendering and record text limits based on measured worst cases.
6. **Distribution.** Expand synthetic public screenshots, supported installation artifacts, authenticated-proxy recipes, Linux/macOS matrix, cache eviction and repair tools. Validate release contents before publishing.

Avoid unmeasured features in the first-view path: full-session attention scans, eager previews for every tool call, global activity statistics and forced Native discovery shutdown.

## Document reader comparison (2026-10-21)

A 739-task real session was used for 100 alternating loopback HTTP requests per endpoint on the same Linux server and Python 3.7 runtime. Candidate and stable instances used separate runtime directories with identical copied review state; Native discovery remained enabled.

| Endpoint | 6.2.1 median / p95 | 6.3.0-dev median / p95 |
| --- | ---: | ---: |
| Session shell | 15.40 / 16.66 ms | 15.90 / 17.66 ms |
| Warm manifest | 15.64 / 17.66 ms | 16.32 / 18.74 ms |
| Task 632 structure | 3.74 / 4.41 ms | 4.12 / 4.64 ms |
| Representative section | 3.84 / 4.22 ms | 4.20 / 4.65 ms |

The shell grew by 1,697 bytes (under 1%). Warm responses remained close and below the existing endpoint targets in this sample. This shared-server test is not a guarantee about other workloads or browser paint. An earlier 20-sample run showed a 41.75 ms candidate task p95; that tail difference did not recur in the 100-sample follow-up. Cold indexing and live-search behavior were not certified anew by this comparison. Index/search algorithms are unchanged; first report requests are independently bounded. Real files, paths and full measurement records remain private.

## Reading refinement comparison (2026-10-21)

The 6.3.0-dev.2 candidate was compared against the deployed 6.3.0-dev version on a growing 744-task session, using 100 alternating loopback HTTP requests per endpoint and the same Python 3.7 interpreter, copied review state and enabled Native discovery.

| Endpoint | 6.3.0-dev median / p95 | 6.3.0-dev.2 median / p95 |
| --- | ---: | ---: |
| Session shell | 16.01 / 18.25 ms | 15.98 / 18.34 ms |
| Warm manifest | 16.16 / 17.78 ms | 16.49 / 18.71 ms |
| Task 632 structure | 3.84 / 4.56 ms | 3.90 / 4.27 ms |
| Representative section | 4.13 / 4.98 ms | 4.08 / 4.76 ms |

The shell increased by 8,670 bytes (4.2%). The largest measured p95 increase was 0.93 ms. This verifies warm HTTP behavior only, not browser paint, cold indexing or first search. Session discovery, indexing and search implementations are unchanged; scroll bookmarks add no network requests.

## Task-count validation (2026-10-21)

The unchanged 6.3.0-dev.2 runtime was exercised with a generated 2,000-task Native session on macOS / Python 3.11.9. A task is a user request and its following responses; this fixture contains 4,001 user/assistant messages plus a small execution-evidence example. The JSONL is 1,506,058 bytes (about 1.44 MiB). This validates task-count handling; the approximately 600 MB real-session workload above is a separate test, not a 2,000-task / 600 MB claim.

- Native discovery enabled; first, 1,000th and 2,000th task payloads checked.
- Real-browser direct navigation to task 2,000, jump to task 1,000 and content-search navigation exercised.
- At task 1,000: 3 task DOM nodes, 16 rendered navigator rows and no horizontal page overflow at the default desktop viewport.
- Source SHA-256 and modification time unchanged after indexing and HTTP checks.

| Local loopback measurement | Result |
| --- | ---: |
| First shell HTTP | 1.06 ms |
| Cold manifest ready, including polling | 38.31 ms |
| Warm shell median / p95, 25 samples | 1.13 / 1.29 ms |
| Warm manifest median / p95, 25 samples | 3.29 / 3.62 ms |
| First unique-marker search HTTP | 19.19 ms |
| Cached marker search HTTP | 0.88 ms |

These are task-count fixture measurements, not browser paint times or guarantees for other hardware, long individual messages or large tool output.

Reproduce with disposable generated data (the tool does not read the user's Codex home):

```sh
python3 tools/demo.py --tasks 2000 --port 17871
```

Open `http://127.0.0.1:17871/session/00000000-0000-4000-8000-000000000001#task-2000`, let preparation finish, then run in another terminal:

```sh
python3 tools/benchmark.py http://127.0.0.1:17871 00000000-0000-4000-8000-000000000001 --query scale-marker-2000 --samples 25
```

The first search is cold only until that query has run; later requests use the existing search cache. Stop the demo with Ctrl+C to remove its generated session directory.

## Product upgrades to evaluate

These are proposals, not features included in the current preview. Keep Native discovery enabled, Codex-owned data read-only and the existing session-entry path free of additional scans.

| Priority | User benefit | Lightweight approach and acceptance |
| --- | --- | --- |
| P1: New-content indicator and explicit Follow latest | Check a running session without losing the paragraph being reviewed | Poll only the active source metadata while visible; reuse append indexing; pause follow on manual reading; no background-tab polling or unsolicited scroll changes |
| P1: Persistent task context | Know which task and time a long answer belongs to | A small current-task breadcrumb based on the existing bounded task window; no extra source requests; keyboard and mobile coverage |
| P2: Faster first search | Find earlier answers in large histories sooner | Evaluate an optional background sidecar index; preserve Chinese substring behavior and short queries; detect SQLite/FTS capabilities and retain streaming fallback; bound CPU, memory and index size |
| P2: Section windows inside exceptional tasks | Keep one huge tool-heavy task responsive | Render visible sections and bounded neighbors while preserving stable section IDs, search reveal, review state and reading anchors |
| P3: Report navigation and image reading | Return to reports and inspect figures more comfortably | Collect report links from already loaded tasks, offer image zoom and document context, and retain configured file roots; no eager full-session report discovery |

Useful implementation references: [VS Code sticky scroll](https://code.visualstudio.com/docs/terminal/shell-integration#_sticky-scroll) keeps command context visible above long output; the same interaction can inform task breadcrumbs. [SQLite FTS5](https://www.sqlite.org/fts5.html#the_trigram_tokenizer) offers substring-oriented trigram indexing, but its minimum-length and runtime-availability constraints must be tested before replacing the existing search path.
