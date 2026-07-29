# pumllint — Security & Hardening Assessment

**Repository:** fdurieux/pumllint · **Version assessed:** 0.24.0 (commit `9fd894d`, branch `main`) · **Date:** 2026-07-29
**Mode:** read-only review; remediation followed on the same branch — see §8.

---

## 1. Verdict

**No exploitable vulnerability was found in the shipped package under its intended trust model, and no secrets exist in the tree or in the full git history.** The codebase is in unusually good security shape for a project of this kind: zero runtime dependencies, no dynamic code loading, safe YAML parsing, a correctly-escaped HTML reporter, an injection-resistant composite GitHub Action, and OIDC Trusted Publishing to PyPI.

Hardening **is** warranted, but it is modest and concentrated in the CI/supply-chain layer, not the Python code: a missing `permissions:` block in `tests.yml`, tag-pinned (rather than SHA-pinned) actions in the workflow that holds the PyPI publishing credential, an unverified `curl` of `plantuml.jar`, and one confirmed robustness bug (malformed config regex → raw traceback instead of the documented clean config error).

Equally important: several hardening measures that a generic checklist would prescribe are **nonsense for this codebase** and should be deliberately skipped (section 5).

---

## 2. Scope and trust model

pumllint is a CLI linter/scorer for PlantUML files, run by developers and CI on **their own repository's** files. That trust model drives every judgment below.

| Surface | What it is | Trust level |
|---|---|---|
| `.puml` inputs | Diagram files under paths the user names | Repo-trusted (same as source code) |
| Config (`pumllint.{yaml,toml,json}`) | Rule options, severities, regexes, `scoring.syntax_command` | Code-adjacent trust — a config **can execute commands** (by design, see F8) |
| Baseline / report files | JSON read/written at user-named paths | User-intended I/O only |
| Reports (text/json/sonar/badge/html) | Emitted to stdout or a named file | HTML may be opened in browsers; text lands in terminals/CI logs |
| Subprocess | `plantuml -checkonly <file>` — opt-in syntax gate | Command string comes from config |
| Supply chain | PyPI package, composite GitHub Action, pre-commit hooks | Consumed by third parties |
| `tools/` | LLM experiment harnesses (Anthropic/Gemini APIs, `gh` harvesting, generated-code runner) | Developer-only; **not** shipped in the wheel (`packages.find` includes `pumllint*` only) |

Complete I/O inventory of the shipped package: reads config/baseline/schema/diagram files; writes only the baseline file, the report output path, and (for `pumllint fix`) the same files it read. No temp files, no network, no environment-variable secrets anywhere in `pumllint/`.

---

## 3. What is already right (verified, not assumed)

These are the reasons the finding list below is short. Each was checked in code, and where possible empirically.

1. **Zero runtime dependencies** (`dependencies = []`). The single biggest supply-chain reduction available to a Python package, already taken. YAML support is an optional extra.
2. **No dangerous primitives in the package.** No `eval`/`exec`/`pickle`/`marshal`; no `shell=True`; rule discovery (`rules/__init__.py`) walks only the package's own modules — there is **no user-plugin loading path**, so a config cannot cause arbitrary imports.
3. **Config parsing is safe by construction**: `yaml.safe_load`, stdlib `tomllib`, stdlib `json` (`config.py`). Non-UTF-8 input files surface as a clean config error (UnicodeDecodeError is a ValueError, which `cli.py` catches → exit 2).
4. **The HTML reporter's claims are true.** Every interpolated value goes through `html.escape` (labels, messages, file paths, dimension names, version); colors come from a fixed dict; no scripts, no external requests. The shipped `docs/example-maturity-report.html` contains zero `<script>` tags.
5. **The composite action (`action.yml`) is injection-resistant.** All inputs travel via `env:` rather than `${{ }}` interpolation inside the script body — the classic GitHub Actions script-injection vector is closed — and the `command` input is allowlisted (`lint|score|fix`).
6. **`publish.yml` follows current best practice**: PyPI **Trusted Publishing (OIDC)** — no stored API token to steal or rotate; top-level `permissions: contents: read`; `id-token: write` scoped to the publish job only; build and publish separated with an artifact handoff; the wheel is smoke-tested from outside the source tree before upload.
7. **`tests.yml` uses `pull_request`, not `pull_request_target`** — fork PRs get no secrets and a read-only token. No secrets are referenced in any test job.
8. **The subprocess gate is disciplined** (`syntax.py`): argv list, `shlex.split` (no shell), timeout with a clean error, opt-in only.
9. **No credentials anywhere.** Pattern scan (Anthropic/Google/GitHub/AWS/Slack key shapes, private-key headers) over the working tree **and all 50 commits of history**: zero matches. The dev tools read API keys from environment variables only.
10. **TLS is never weakened.** The one hand-rolled HTTP client (`tools/codegen_experiment.py`, Gemini) uses `ssl.create_default_context` with certifi; no `verify=False`, no `CERT_NONE` anywhere.
11. **External-data filename handling is sanitized**: `harvest_corpus.py` flattens harvested repo/path names through `[^A-Za-z0-9_.-] → _` before writing — no path traversal from search results.
12. **The JSON-Schema validator fails closed** (`schema.py` rejects unknown keywords rather than ignoring them), and baseline files are version-checked and type-coerced on load.

---

## 4. Findings — hardening that makes sense

No finding is Critical or High. Ranked by value-for-effort.

### F1 · `tests.yml` has no `permissions:` block — **Medium** (CI hardening)
The workflow inherits the repository's default `GITHUB_TOKEN` grant, which depends on the repo's *Workflow permissions* setting (historically read/write). Every job in `tests.yml` only checks out and runs tests. One line at the top (`permissions: contents: read`) makes least-privilege invariant regardless of repo settings, and is the first thing OpenSSF Scorecard flags. `publish.yml` already does this — `tests.yml` should match.

### F2 · Actions pinned by mutable tag/branch, not commit SHA — **Medium** (supply chain)
`actions/checkout@v5`, `actions/setup-python@v6`, `upload/download-artifact@v4` and — most importantly — `pypa/gh-action-pypi-publish@release/v1` are all mutable references. `release/v1` is a **moving branch**, and it sits in the job that holds the OIDC identity able to publish `pumllint` to PyPI: a compromise of that action becomes a compromise of your package. The 2025 `tj-actions` incident demonstrated exactly this tag-rewrite path. GitHub-owned `actions/*` are lower risk; the pypa action is the one that matters.
**Sense:** SHA-pin at minimum `publish.yml` (pypa's own docs support pinning an exact commit), ideally all workflows — **paired with F6's Dependabot config**, because SHA pins without automated update PRs rot into a different risk (running stale, unpatched actions).

### F3 · `plantuml.jar` fetched by `curl` and executed without checksum verification — **Low/Medium**
`tests.yml` (syntax-gate job) downloads a version-pinned jar from GitHub releases and runs it. Release assets are mutable if the upstream account is compromised. Blast radius is one CI runner — but combined with F1's default token that runner may hold write credentials, which is how the two findings compound. Pinning a SHA-256 alongside `PLANTUML_VERSION` is a three-line fix.

### F4 · Malformed config regex crashes with a raw traceback — **Low/Medium** (robustness bug, confirmed)
Six rule options are user-supplied regexes compiled/used without error handling: `codegen.py:116` (SEQ103 `pattern`), `class_/structure.py:31-32` (`class_pattern`, `member_pattern`), `governance.py:68/118/143` (naming, owner-tag, requirement-link), `activity/structure.py:127` (swimlane pattern). Verified empirically: `pattern = "("` in a TOML config produces an unhandled `re.error` traceback and **exit 1**, violating the CLI's documented contract (exit 2 = usage/config error) — in CI, that misreports a broken config as "lint findings". Also, a config regex runs with arbitrary complexity against diagram text (ReDoS-from-config), though config is trusted, so the traceback is the real issue.
**Sense:** wrap compilation, re-raise as `ValueError` naming the rule id and option → the existing handler turns it into a clean exit-2 config error. Small, high-value.

### F5 · Repo hygiene files missing: SECURITY.md and Dependabot — **Low**
For a package published on PyPI, with a GitHub Action and pre-commit hooks consumed by third parties, there is currently no security policy (no reporting channel) and no `dependabot.yml`. **Sense:** add `SECURITY.md` (contact + supported-versions line) and Dependabot for `github-actions` (enables F2 sustainably) and `pip` (covers the test extras). Both are configuration, not code.

### F6 · Terminal escape injection via diagram content in text output — **Low**
Violation messages embed raw diagram text (message labels, participant names) and the text reporter prints them verbatim. A malicious `.puml` can therefore inject ANSI/OSC sequences into terminals and CI logs (log spoofing, hyperlink/title tricks). Under the trust model this needs a hostile file in your own repo — but it's the one place linter output renders untrusted bytes into a terminal, several mainstream linters have shipped fixes for the same class, and stripping C0/C1 control characters in the text reporter is cheap.

### F7 · The acceptance "sandbox" is a soft guard — **Low** (dev tools only)
`tools/acceptance/runner_child.py` executes **LLM-generated Python** with: `python -I`, stdin closed, 15 s timeout, and `socket.socket` monkeypatched out. That stops accidents, not intent — generated code can still `import _socket`, spawn `subprocess`, write files, or exhaust memory. Today's inputs are your own experiment outputs, so this rates Low. **Sense:** either add `resource.setrlimit` (CPU/address-space) to the child — a few lines matching the guard's spirit — or amend the docstring from "sandboxed" to "best-effort isolation, not a security boundary". Containerize only if these harnesses ever run third-party-influenced code.

### F8 · `scoring.syntax_command` executes arbitrary commands from config — **Info** (document, don't change)
Intentional and correctly implemented (no shell). It does mean *"linting a repo with an untrusted pumllint config can execute commands"* — the same property pre-commit and Makefiles have. No code change; add one sentence to README/`docs/setup-and-ci.md` stating the config file carries code-level trust, so nobody points pumllint + auto-detected config at an untrusted checkout by mistake. The action's `config`/`extra-args` inputs cross no boundary (workflow authors already run arbitrary code).

### F9 · Publishing gates live in repo settings — **Info** (verify, not code)
`publish.yml` fires on any `v*` tag push, so anyone with push access can trigger a release. Worth verifying on the GitHub/PyPI side (not visible from the working tree): the `pypi` **environment** has protection rules (required reviewer, or at least a deployment-branch/tag policy); tag protection for `v*`; branch protection on `main`. These turn "can push" ≠ "can publish".

---

## 5. Nonsense — hardening to deliberately skip

Standard prescriptions that do **not** fit this codebase, with the reason:

| Prescription | Why it's nonsense here |
|---|---|
| Sandbox the linter against hostile `.puml` input; add input-size caps and memory limits | Diagram files carry the same trust as the source code next to them. Worst realistic case is a slow CI job, which CI timeouts already bound. |
| Replace regex parsing with RE2 or a "safe" grammar over ReDoS fears | Inspected the parser regexes: all line-anchored, per-line matching, character-class quantifiers — no nested-quantifier catastrophic-backtracking shapes. Rewriting the parser for a non-existent exposure would be pure cost. |
| Add a lockfile / pin runtime dependencies | There are none to pin. Don't invent a lockfile ritual for the empty set. (Pinning `pytest` in CI: harmless, near-zero value.) |
| Generate SBOMs | The SBOM would read "Python stdlib + pumllint". Produce one only when a downstream consumer contractually asks. |
| Manual GPG signing of releases | Trusted Publishing already binds artifacts to this repo+workflow via OIDC, and the pypa action publishes PEP 740 attestations. Manual signing adds key-management burden for no additional assurance. |
| Harden `pumllint fix` against symlink/TOCTOU attacks in the checkout | The tool edits files its invoker named in their own working tree; an attacker positioned to plant symlinks there already owns the checkout. |
| Secrets-management tooling / token rotation procedures | Verified: there are no secrets in tree or history, and publishing is tokenless (OIDC). There is nothing to manage. |
| CSP meta tags or JS hardening for the HTML report | The report is static, script-free, fully escaped, self-contained — correct by construction. A CSP tag would be cargo cult. |
| Heavy config-schema validation layer | Config values are booleans, severity enums (already validated via `Severity()` → clean error), and patterns (fix via F4). A validation framework adds surface, not safety. |
| Fuzzing the parser as a security measure | As *security*, unnecessary (crash = lint job fails safely). As *quality* engineering for parser robustness, a one-off fuzz run is a reasonable optional extra — just don't file it under security debt. |

---

## 6. Method and limits

Reviewed: all of `pumllint/` (CLI, engine, config, parser regexes, rules incl. option handling, reporters, fixer, baseline, schema, syntax gate), both workflows, `action.yml`, `.pre-commit-hooks.yaml`, packaging metadata, and the security-relevant paths of `tools/` (LLM harnesses, corpus harvesting, acceptance runner). Pattern sweeps for dangerous primitives and credentials covered the tree and all 50 commits of history. F4 was confirmed by running the CLI against a malformed config. Not done: OpenSSF Scorecard/CodeQL runs, GitHub repo-settings audit (F9 lists what to check), and adversarial regex fuzzing (complexity assessed by inspection).

---

## 7. If you say go — proposed order of work

1. **F1** — `permissions: contents: read` in `tests.yml` (1 line).
2. **F2 + F5** — SHA-pin actions (publish.yml first) and add `dependabot.yml` (actions + pip) so pins stay fresh; add `SECURITY.md`.
3. **F3** — checksum-verify `plantuml.jar`.
4. **F4** — catch `re.error` on the six config-regex sites → clean exit-2 config error (+ test).
5. **F6** — strip control characters from text-reporter output (+ test).
6. **F8** — one documentation sentence on config trust.
7. **F9** — verify `pypi` environment protection, tag protection, branch protection in repo settings (no commit involved).
8. **F7** — rlimits in `runner_child.py` or an honest docstring.

Items 1–6 and 8 are all small, self-contained changes on the order of a few lines each; nothing requires restructuring.

---

## 8. Resolution (2026-07-29, this branch)

| Finding | Status | What was done |
|---|---|---|
| F1 | **Fixed** | `permissions: contents: read` at the top of `tests.yml`. |
| F2 | **Fixed** | All five actions SHA-pinned with version comments (checkout v5.1.0, setup-python v6.3.0, upload-artifact v4.6.2, download-artifact v4.3.0, pypi-publish v1.14.1 — the commit `release/v1` pointed at when pinned, so behavior is unchanged). |
| F3 | **Fixed** | `PLANTUML_SHA256` pinned next to `PLANTUML_VERSION`; `sha256sum -c` gates execution of the downloaded jar. |
| F4 | **Fixed** | `compile_option_pattern` / `Rule.pattern_option` in `pumllint/rules/__init__.py`; all six sites converted (GEN004 incl. `per_kind`, GEN006, GEN007, CLS001 ×2, ACT005, SEQ103). Malformed patterns now exit 2 with `error: rule <ID>: option '<name>' is not a valid regex …` (verified). Regression tests in `tests/test_hardening.py`. |
| F5 | **Fixed** | `.github/dependabot.yml` (github-actions grouped monthly + pip) and `SECURITY.md` (private reporting channel, supported versions, trust-model scope). |
| F6 | **Fixed** | `sanitize_terminal` in `pumllint/reporters/base.py` (C0 minus tab, DEL, C1 → U+FFFD), applied per logical line in the text reporter and the two CLI prints that embed diagram content (fix descriptions, baseline regressions). Deliberate exception: `pumllint fix --dry-run` diff output stays raw — it is a patch, with the same trust properties as `git diff`. Verified end to end; tests in `tests/test_hardening.py`. |
| F7 | **Fixed** | `runner_child.py` docstring now states the guard is best-effort accident prevention, not a security boundary; added rlimits — RLIMIT_AS 2 GiB (a memory bomb now surfaces as a reported `MemoryError` instead of starving the host — verified) and RLIMIT_CPU 30 s, deliberately *above* the parent's 15 s wall kill so the parent keeps owning the frozen `timeout` classification. |
| F8 | **Fixed** | Config-trust note in README (§Configuration), `docs/setup-and-ci.md`, SCORING.md (`--check-syntax` bullet), codified in `SECURITY.md`. |
| F9 | **Fixed** (settings applied 2026-07-29, verified) | Applied by the maintainer via `gh api` and re-verified against live state: the `pypi` environment requires reviewer approval (fdurieux) and deploys only from `v*` tags — **each release now pauses for a one-click Approve under Actions**; active rulesets `protect-main` (no force-push, no deletion; direct pushes still allowed) and `protect-release-tags` (`v*` tags create-only — no move, no delete); private vulnerability reporting enabled (the "Report a vulnerability" form referenced by `SECURITY.md` is now live); secret scanning + push protection enabled; Dependabot alerts enabled (version updates proven working — the first grouped action-bump PR arrived within hours and was reviewed and merged). The Actions default `GITHUB_TOKEN` was measured already read-only (pre-hardening job log: `Contents/Metadata/Packages: read`), so no change was needed there. PyPI side verified by the maintainer: a single Trusted Publisher row exactly matching repo `fdurieux/pumllint` + workflow `publish.yml` + environment `pypi`, zero project-scoped and zero account-level API tokens (publishing is OIDC-only, nothing to steal or rotate), and account 2FA enrolled (TOTP + recovery codes). |

Both suites pass after remediation: 338/338 (zero-dependency runner) and 447/447 (pytest incl. BDD), plus the workflow/dependabot YAML parse-checked. With F9's settings applied, every finding of this assessment is closed; the recurring residue is reviewing Dependabot's grouped action-pin PRs and recomputing `PLANTUML_SHA256` on PlantUML bumps.
