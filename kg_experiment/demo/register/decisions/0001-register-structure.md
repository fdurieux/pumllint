# 0001 — One repository, one directory per taxonomy, hierarchy in data

Date: 2026-10-30. State: approved (fdurieux). Supersedes: none.

## Decision

`ieam-register` is one repository with one directory per IEAM taxonomy. The hierarchy is the
`parent` field in each node file, never nested folders per level. Typed cross-domain
relationships live under `relationships/`, one file per type, with a type header and `[[link]]`
instances. Approval is a recorded file-state change. Exports are dated, append-only mirrors
with a manifest; derived outputs are dated reports written at a tag.

## Why

The IEAM calls its levels illustrative and gives each domain its own depth; a per-level folder
freezes them and makes every re-parenting a file move. A per-repository split puts the
dangling-link check across repository boundaries for no gain. Git is authoritative only for
what the sources of record cannot carry; copying their content would make a second record.

## Record

pumllint `docs/ieam-register-proposal.md` (#239), sections 1, 2 and 3.
