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
| Session shell | 15.85 / 17.40 ms | 15.91 / 20.71 ms |
| Warm manifest | 16.30 / 19.54 ms | 16.23 / 18.26 ms |
| Task 632 structure | 4.22 / 6.26 ms | 4.21 / 5.58 ms |
| Representative section | 4.17 / 5.27 ms | 4.27 / 7.03 ms |

The shell increased by 8,600 bytes (4.2%). The largest measured p95 increase was 3.31 ms. This verifies warm HTTP behavior only, not browser paint, cold indexing or first search. Session discovery, indexing and search implementations are unchanged; scroll bookmarks add no network requests.
