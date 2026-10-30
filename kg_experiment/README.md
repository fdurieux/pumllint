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
| `harness/` | the loaders, rules, gate, projection and arms (added by the run commit) |
| `results/` | per scenario and arm, the outputs, suite verdicts and usage (added by the run commit) |

Requirements to reproduce: a Neo4j 5.26 community server on
`bolt://localhost:7687`, Python 3.13 with `neo4j`, `pyyaml`, `rdflib`,
`pyshacl`, `openai` and this repository installed; an OpenAI API key
for the arms. The deterministic half (D1–D6) needs no key.
