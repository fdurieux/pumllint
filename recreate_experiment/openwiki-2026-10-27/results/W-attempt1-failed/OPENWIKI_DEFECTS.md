# Defects found in OpenWiki 0.7.2 while running Arm W (2026-10-28)

Found running `openwiki --print --init` (0.7.2, `deepagents` 1.13.2,
Node 22.22.0, `openai` / `gpt-5.6-terra` / `xhigh`, page concurrency 1)
over the clean room (`535982e6…`). Attempt 1 exited 1 after 396 s with no
page written; `run.log` beside this file. Only the plan and the error path
were read; no page content exists. Each entry says how it was established.

## D1 — a failed first page attempt aborts the whole `--init` (blocking)

**Symptom.** `Could not restore /openwiki/architecture/data-layer.md: Error
deleting '/openwiki/architecture/data-layer.md': ENOENT: no such file or
directory, lstat '…/room-W/openwiki/architecture'`, exit 1, `.run.json`
left at `phase: generating` with all 8 planned pages `pending`,
`.last-update.json` `status: interrupted`.

**Path.** `dist/agent/repository-runner.js` `runPageAgent`: attempt 1 returns
`skipped`; before attempt 2 it calls `restoreRepositoryPage(run, snapshot)`.
For a page that did not exist before the run, `snapshot.markdown === null`,
so `restoreRepositoryPageMarkdown` (`dist/generation/repository-run.js:679`)
calls `run.backend.delete(path)` and tolerates the error only when
`isNotFoundBackendError` (`:256`) holds: `error === "file_not_found" ||
error.includes("not found")`.

**Cause, two packages.** `deepagents` `FilesystemBackend.delete` returns
`"Error: '<p>' not found"` when the *file* is absent, but in `virtualMode`
it first calls `resolveDeletePath`, which `lstat`s every parent segment
without a catch. When the *parent directory* is absent too (every nested page
of a fresh `--init`), that `lstat` throws, and the outer catch returns
`"Error deleting '<p>': ENOENT: no such file or directory, lstat …"`. That
string has no `not found`, so OpenWiki raises `RepositoryRunError
("invalid_state")` and the run dies instead of retrying.

**Reach.** Any `--init` where a page under a subdirectory (`architecture/`,
`concepts/`, `operations/` …) fails its first worker attempt. Seven of the
eight planned pages here were nested. The retry that `PAGE_WORKER_ATTEMPT_LIMIT
= 2` promises never happens for them.

**Reproduced in isolation** (no model call):

```js
import { FilesystemBackend } from "<openwiki>/node_modules/deepagents/dist/index.js";
const b = new FilesystemBackend({ rootDir: process.argv[2], virtualMode: true });
await b.delete("/absent.md");                          // {error: "Error: '/absent.md' not found"}
const r = await b.delete("/openwiki/architecture/x.md"); // {error: "Error deleting …: ENOENT … lstat …/openwiki"}
const isNotFound = (e) => e === "file_not_found" || e.includes("not found"); // OpenWiki's, verbatim
isNotFound(r.error);                                   // false
```

**Fix, either side.** OpenWiki: also accept `ENOENT` in
`isNotFoundBackendError`, or skip the delete when the snapshot recorded no
file. `deepagents`: catch `ENOENT` in `resolveDeletePath`'s parent walk and
return the same `not found` error the file case returns.

## D2 — the first attempt's failure is swallowed

**Path.** `runPageAgent` keeps `outcome.error` only in a local
(`skipped = outcome`), and `runPageWorkerAttempt` returns `{status:
"skipped", snapshot}` with no error at all when the worker exits without
calling `submit_page`. Nothing is logged under `--print`: `run.log` holds the
D1 message and nothing about why page 1 did not submit. D1 then replaces it
with an unrelated filesystem error. Established by reading the code and the
log.

**What it hid, found 2026-10-28** with a diagnostic copy that logs
`outcome.error` (one `console.error` added after `skipped = outcome;`), run
in a throwaway room whose wiki was not read: `Error: 502 upstream request
failed`, raised through `langchain`'s `MiddlewareError.wrap`. The same D1
abort followed. The 502 is the session's agent proxy's, not OpenAI's. A bare
`POST /v1/responses` (`gpt-5.6-terra`, `xhigh`) through it fails with the
same body at 30.4 s; the same request with `"stream": true` returns 200
after 128 s, first byte at 0.85 s. OpenWiki sends provider `openai`
non-streaming: `providerUsesStreaming` (`dist/config/constants.js:390`)
returns `true` only for `copilot`, `bob` and opt-in `openai-compatible`.
Its own comment on `bob` names this failure ("Long generations … can outlast
the endpoint's response timeout when sent as a single non-streaming
completion"). So an `xhigh` page call that takes over 30 s to produce
anything cannot pass this proxy. That is an environment limit, not an
OpenWiki defect, but D2 made it look like a filesystem error, and D1 made
one transient provider error fatal.

## D3 — no `--version` (minor)

`openwiki --version` and `openwiki -v` print `Unknown option: --version` /
`-v`; the first exits 1. `--help` lists no version flag, though the banner
prints `v0.7.2`. Pinned-version checks have to read
`$(npm root -g)/openwiki/package.json`.

## Not OpenWiki's

- **Proxy.** Node's built-in `fetch` ignores `HTTPS_PROXY` unless
  `NODE_USE_ENV_PROXY=1` (Node ≥ 22.21). The environment's proxy injects the
  OpenAI key only for traffic that reaches it, so the run needed that
  variable. That is Node's default, not an OpenWiki defect, though OpenWiki's
  docs could say so.
- **Ours, fixed on this branch.** `tools/run_openwiki.sh` relied on D3's
  absent flag, and lost `PROVENANCE.json` on a page-less run (`pipefail` over
  `find` on a missing `.claims/`).
