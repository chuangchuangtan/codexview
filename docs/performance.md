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

1. Expand representative CLI schema/tool fixtures and repeatable first-paint browser benchmarks, including mobile gestures and slow storage.
2. Evaluate compact postings for faster cold queries without changing Unicode substring semantics; the current optional sidecar remains sequential.
3. Add turn-aware migration fixtures before changing task identity or review mappings.
4. Expand authenticated-proxy recipes, distribution validation and user-facing cache maintenance.

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

## P1–P3 implementation in 6.3.0-dev.3

The following upgrades are implemented. Native discovery remains enabled and Codex-owned data stays read-only. See [controls and limits](continuous-reading.md).

| Priority | User benefit | Lightweight approach and acceptance |
| --- | --- | --- |
| P1: New-content indicator and explicit Follow latest | Check a running session without losing the paragraph being reviewed | Poll only the active source metadata while visible; reuse append indexing; pause follow on manual reading; no background-tab polling or unsolicited scroll changes |
| P1: Persistent task context | Know which task and time a long answer belongs to | A small current-task breadcrumb based on the existing bounded task window; no extra source requests; keyboard and mobile coverage |
| P2: Faster first search | Find earlier answers in large histories sooner | Explicit compressed text sidecar; Chinese substrings and short queries retained; append updates/cancellation, 128 MiB per cache, two ready caches plus one temporary build; streaming fallback; no SQLite dependency |
| P2: Section windows inside exceptional tasks | Keep one huge tool-heavy task responsive | 24-section chunks for tasks over 72 sections; normally five mounted chunks plus visible/focused/search targets; stable section IDs and search/bookmark reveal |
| P3: Report navigation and image reading | Return to reports and inspect figures more comfortably | Collect up to 120 loaded report links; local image zoom and up to 80 HTML image links with report context; configured file roots retained |

Useful implementation references: [VS Code sticky scroll](https://code.visualstudio.com/docs/terminal/shell-integration#_sticky-scroll) keeps command context visible above long output; the same interaction can inform task breadcrumbs. [SQLite FTS5](https://www.sqlite.org/fts5.html#the_trigram_tokenizer) offers substring-oriented trigram indexing, but its minimum-length and runtime-availability constraints must be tested before replacing the existing search path.

## Continuous reader comparison (2026-10-21)

Compared 6.3.0-dev.3 with the preserved 6.3.0-dev.2 on the same 755-task, 615,727,863-byte Native session and Python 3.7 server. Each endpoint has 100 alternating loopback samples; separate runtimes, Native discovery enabled, copied review state. These are HTTP timings, not browser paint times.

| Endpoint | dev.2 median / p95 | dev.3 median / p95 |
| --- | ---: | ---: |
| Session shell | 15.36 / 16.54 ms | 16.02 / 17.63 ms |
| Warm manifest | 15.42 / 19.46 ms | 16.76 / 19.38 ms |
| Task 632 | 3.70 / 4.29 ms | 4.07 / 5.03 ms |
| Representative section | 3.78 / 4.35 ms | 4.13 / 4.47 ms |

The shell grew by 19,791 bytes (9.3%); all endpoint p95 values remain below the existing targets. Cold indexing was not re-certified; its algorithm and persisted manifest version are unchanged. Optional relationship, report and cache reads do not run during entry.

For three distinct queries (one English filename, one Chinese phrase, one absent marker), baseline streaming took 6.51 / 5.59 / 6.83 seconds; prepared compressed-cache queries took 3.71 / 3.55 / 2.82 seconds, with identical ordered results. This is one query comparison per case, not a percentile claim. Explicit cache preparation took 11.35 seconds and covered the complete source within the 128 MiB cap. Cache preparation is not part of ordinary entry or query latency; repeating the same query uses the existing query-result memory cache. Performance can vary with storage contention and oversize records.

Browser checks on a generated 2,000-task session exercised five successive native Page Down actions, followed by five Page Up actions. Recorded scroll positions advanced and reversed by 680 px per page without rewinding after hydration; three task DOM nodes remained. Separate DOM integration covers user movement during an 80 ms pending payload, deep section 479 of a 480-section task, visible-only polling, follow pause, reports and image zoom. Synthetic append testing exercised a new task arriving while Follow latest was active. These checks do not certify every possible image layout or touchscreen device.

## Task-window repair (2026-10-25)

Compared dev.5 against deployed dev.4 on the same 839-task, 697,452,685-byte Native session and Python 3.7 server, using 50 alternating loopback requests per endpoint and separate runtime directories. These are HTTP timings, not browser paint.

| Endpoint | dev.4 median / p95 | dev.5 median / p95 |
| --- | ---: | ---: |
| Session shell | 15.33 / 19.45 ms | 15.48 / 17.30 ms |
| Warm manifest | 15.95 / 16.92 ms | 16.58 / 17.76 ms |
| Task 830 structure | 3.74 / 4.16 ms | 4.05 / 4.60 ms |
| Representative task 830 section | 3.70 / 4.47 ms | 4.09 / 4.86 ms |

The shell grew by 2,761 bytes (1.2%); no discovery/index/search algorithm changes or third-party runtime dependencies were introduced. Real-browser validation covered 48 Page Down/Page Up/direction-change actions around tasks 830–834 and 12 wheel actions, with no duplicate task IDs, at most three task nodes, and no browser errors. A dedicated geometry fixture also checks measured spacer replacement with unequal heights, replayed insertion, stale prefetch and cancelled payload recovery. The earlier uniform-height fixture did not cover those cases. This does not certify every image/font layout or touchscreen device.
