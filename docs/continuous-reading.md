# Continuous reading (6.3.0-dev.5)

Updated 2026-10-25 (Asia/Shanghai). This is a development preview.

Version 6.3.0-dev.5 unifies window commits and makes task insertion idempotent. Ordinary scroll selection no longer calls the explicit navigation routine or cancels prose requests. A measured task stays represented by its spacer until the replacement node is mounted at its remembered height; stale prefetches and detached observer entries are ignored. Paragraph anchors fall back to their section/task if a payload is replaced.

6.3.0-dev.5 统一任务窗口更新，同一任务只保留一个节点。滚动切换不再重启阅读器；旧任务恢复时先用实测高度替换占位，再加载正文，忽略过期请求，保留段落位置。

## Reading controls / 阅读操作

| Control | Behavior / 行为 |
| --- | --- |
| Task title and time | Sticky context follows the visible task without source requests. 顶部保留当前阅读任务的标题与时间。 |
| New content · Refresh | Checks the current source stat every four seconds while visible. Does not index or move the reader until selected. 页面可见时检查元数据，提示后由读者决定刷新。 |
| Follow latest | Opt in to refresh and jump to the latest task. Wheel, touch, reading keys and manual task/filter navigation pause following. 主动开启跟随，手动翻阅即暂停。 |
| Search → Build search cache | Explicit background preparation; Cancel keeps an existing usable cache. 主动后台准备，可取消，不影响旧缓存。 |
| Reports | Up to 120 unique report links collected from loaded tasks; no full-session scan. 汇集已经加载的任务中的报告链接。 |
| Related | Parent/fork metadata only; inspect 128 discovered session headers per page, each at most 64 KiB. 仅依据明确声明的关系，可按页继续检查。 |
| Images | Click a local Markdown image to zoom. HTML's Images menu lists up to 80 approved local images and preserves report/task return links. 本地图片放大，保留返回报告和任务的入口。 |

Reading positions remain browser-local. Explicit task navigation seeks once; asynchronous hydration does not seek again. Evicted tasks retain their measured height, and adjacent prose is prefetched near the reading window. At most three task DOM nodes remain. Tasks with more than 72 sections use chunks of 24 sections; normally five chunks stay mounted, with additional visible, focused or search-target chunks retained. Estimated heights for unseen content can still change as it loads; viewport anchors compensate for changes above the reader. This does not promise zero layout shift for every image or unusually large paragraph.

阅读位置仅存于当前浏览器。跨任务翻阅保留已移出内容的实测高度；单个任务超过 72 个 section 时按 24 个一组加载，通常保留五组，当前可见、焦点及搜索命中内容另行保留。未读取内容的高度仍为估计值，不能保证所有图片和极长段落完全没有布局变化。

## Search cache / 搜索缓存

Native search can use an optional compressed, lowercase-text sidecar. It is a sequential accelerator, not a full-text postings index; it preserves the existing two-character minimum and Chinese/English substring behavior. Matching records and snippets are checked against the original JSONL. Oversize records and an uncovered file tail use the original streaming path. Results remain limited to 200 matching records, with the existing 12-query memory cache for repeated queries.

The cache never builds on entry, freshness polling or an ordinary query. Choose Build, then Update after source appends if desired. Each ready cache is capped at 128 MiB; two are retained, plus at most one temporary 128 MiB build. One background builder runs, with at most two queued/running jobs. Cancellation retains the previous cache. Source replacement, incompatible metadata, corruption or unavailable cache storage falls back to streaming search. No SQLite extension or third-party runtime dependency is required.

缓存按需准备，不是倒排索引。中文与英文子串语义保持一致，命中结果回读原记录验证。每份最多 128 MiB，保留两份，构建时最多增加一份临时空间；一次仅运行一个构建任务。追加、取消、缓存失效或空间上限均有流式回退。超大记录仍由原始搜索路径读取。

Caches contain readable conversation text. Protect `$CODEX_HOME/codexview/` with the same filesystem/network access policy as the viewer. Source rollouts, Codex config and authentication data stay strictly read-only. Optional cache files, bookmarks, review state and report navigation do not change session identity or require resuming Codex CLI. Native session discovery remains enabled.

## Remaining limits

Freshness watches the open session, not newly created sessions; use the library's Refresh to rediscover sessions. Relationships without explicit metadata are not inferred. Reports are collected only from read tasks. Search-cache construction can use noticeable CPU and disk bandwidth while active. There is no built-in authentication, multi-user review isolation, CLI execution or live HTML scripting.

See [performance scope](performance.md), [report reader boundaries](document-reader.md) and [data safety](../SECURITY.md).
