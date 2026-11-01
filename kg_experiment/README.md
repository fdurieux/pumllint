# kg_experiment — governed knowledge in a graph store (opened 2026-10-30)

A pre-registered proof of concept behind
`docs/neo4j-governed-knowledge-evaluation.md`: the CargoQuote kit
(`../stack_experiment/cargo_quote/`) loaded into a local Neo4j 5.26
community server as assertions with provenance, epistemic basis,
status, verification records, gaps and conflicts; seven scenarios from
the maintainer's research prompt planted mechanically; a gate that
resolves a task's required knowledge to a verdict; and two generator
arms (documents against the graph's evidence bundle) graded by the
kit's execution oracle. Read `PREREGISTRATION.md` first; its Results
section is the record.

Lab territory under the packaging settlement: nothing here ships in
the product, and the product path stays deterministic. The
2026-08-26 knowledge-graph settlement (N1–N5) is untouched.

| path | what |
|---|---|
| `PREREGISTRATION.md` | question, subject, metamodel, rules, the seven scenarios and their plant, the gate, arms, measures D1–D6 and M1–M7, expectations X1–X10, interpretation matrix, budget, bounds; Results below the line |
| `kit/` | the three authored inputs (`requirements.md`, `quote_process.bpmn`, `screening_decision.dmn`), the human-authored link set (`links.toml`) and the suite→assertion verification map (`verification_map.toml`) |
| `harness/`, `demo/` | moved to `fdurieux/knowgov` on 2026-11-01 (ROADMAP, that date): the pipeline as a subject-generic harness with a store port, and the demo container. In this repository's history: `cf9d919` is the harness that produced `results/` (its `SHA256SUMS` names those files), `3cd7fc2` the last tree carrying both |
| `results/` | per scenario: `deterministic.json` (D1–D6), the prompts and the governed bundle, `run<i>_<arm>.json` with the raw response and the code; `summary.json`, `usage.json`, `SHA256SUMS`; `rerun/S6/` the S6 re-run with the corrected bundle; `d3check/S6/` the deterministic re-establishment of D3 after the loader fix |

Requirements to reproduce: the harness at `cf9d919`
(`git checkout cf9d919 -- kg_experiment/harness`), a Neo4j 5.26 community
server on `bolt://localhost:7687`, Python 3.13 with `neo4j`, `pyyaml`,
`rdflib`, `pyshacl`, `openai` and this repository installed; an OpenAI API
key for the arms. The deterministic half (D1–D6) needs no key. Or start
knowgov's `demo/` with `docker compose up`, which brings all of that up in
two containers against its vendored copy of this record (its
`demo/README.md`).
