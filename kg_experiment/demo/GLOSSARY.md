# Glossary and writing rules for the demo page

The demo page explains the Neo4j governed-knowledge experiment to a
reader who has never seen it. Every sentence the page generates for that
reader follows the rules below, modelled on Simplified Technical English
(ASD-STE100): one approved word per concept, short sentences, and no
synonyms. The rules are checked, not hoped for: `views.py` registers every
sentence it generates with its kind, and `tests/test_kg_demo.py` fails
when a sentence breaks a rule.

## The rules

1. **One term per concept.** Use the approved term from the table below,
   never one of its forbidden synonyms. A reader who meets "assertion"
   in one place and "statement" in another cannot know they are the same.
2. **One idea per sentence.** A *controlled* sentence has at most 20
   words. A *reading* (the "what this shows" paragraph of each scenario,
   which interprets rather than reports) has at most 25.
3. **Numbers come from the files.** A sentence that carries a count reads
   it from `deterministic.json` or a run file; nothing is typed in.
4. **Data is quoted as it is.** The gate's reason, a conflict's text, a
   list of assertion ids or an engine message is *data*: it is shown
   verbatim and exempt from the length rule, because rewording it would
   make it a second source.
5. **Active voice where the actor matters.** "The gate blocked" rather
   than "the key was blocked", so the reader learns who does what.
6. **Define before use.** The page's first paragraph names the pipeline's
   terms in order; the glossary card under it defines each one.

## Kinds of sentence

| kind | where | limit | checked for synonyms |
|---|---|---|---|
| controlled | the plain-English block, the stage panels, the gap kinds, the scenario cards and the Planted line, the pipeline boxes' labels and lines, the systemic-model panels and captions, the register view and its panels, the footprint box and panel, the reference panels and the hover tips | 20 words | yes |
| reading | `SCENARIOS[..]["plain"]`, the "what this shows" paragraph | 25 words | yes |
| data | the gate's reason, conflict texts, id and key lists, engine and API messages, the model's own labels and definitions | none | no |

## Approved terms

The authoritative table is `GLOSSARY` in `kg_experiment/demo/app/views.py`;
the page shows it as the *Glossary* card under the plain-English block,
and the test checks this file names every term of it.

| term | meaning |
|---|---|
| document | One of the kit's input files, such as a decision table or a diagram. |
| fragment | A piece of a document, such as one table row, stored with its own digest. |
| digest | A fingerprint of some bytes; when the bytes change, the digest changes. |
| entity | A thing the documents talk about, such as a pricing step or a requirement. |
| assertion | One fact read from a document: an entity, a property and a value. |
| basis | How an assertion came to exist: authored by a person, extracted by a parser, or inferred by a model. |
| status | Where an assertion stands: proposed, validated, verified, approved, disputed or invalidated. |
| rule | One of the seven checks the harness runs on the store after each load. |
| gap | Something a rule found wanting: missing, ambiguous, a conflict, or unverified. |
| key | One piece of knowledge the coding task needs; the task needs 36 keys. |
| gate | The check that reads the 36 keys and gives a verdict. |
| verdict | The gate's answer: PROCEED, QUALIFIED or BLOCKED. |
| bundle | The text the gate writes for arm G: the verdict, the policy and the evidence per key. |
| arm | One of the two AI assistants asked to write the code. G got the bundle; B got the documents. |
| run | One call of one arm, graded on its own. |
| decision | The word an arm gives for its own choice: generate, generate with assumptions, or abstain. |
| oracle | The kit's eleven acceptance scenarios, run on the code an arm wrote. |
| planted target | The oracle scenario the planted defect aims at. |
| flagged | The arm named the planted problem in its questions or assumptions. |
| record | The committed results of the scored run, under results/. |
| demo run | A re-run written to a dated folder under results/demo-runs/. |
| store | The Neo4j database the harness loads; it holds one scenario at a time. |
| model | The language model that answers an arm's call. |
| node | One record of one register taxonomy: a capability, product, journey element, process element, application element, information node or organisation unit. |
| link | One typed, directed relationship between two register nodes, with its own id, state, owner and approval. |
| relationship type | One of the register's ten typed relationships, such as requires, realizes, supports or manages. |
| source of record | The system that authors a node's content: ARIS, Archi, the EDM repository, or the kit in the test case. |
| export | A dated, append-only mirror of a source of record, with a manifest of digests and a reconciliation report. |
| approval | A recorded acceptance: of a verified assertion in the store, or of a node or link in the register, with who, when and which record. |
| exception | An approved, expiring deviation from a coverage rule, with its scope and rationale. |
| coverage rule | A register check that an approved node of one kind has a link of one type, or an unexpired exception. |
| state | Where a register node or link stands: draft, proposed, approved, deprecated, retired or rejected. An assertion has a status, never a state. |
| footprint | The register nodes and links a scenario touches: through its keys below approved, its requirement gaps and its changed documents, by the demo's approved map. |
| reference | An underlined cell of a panel's table that opens its subject's own panel under the table: a node, a link, a requirement, a key or a document. |
| projection | The register's nodes and links loaded into the store in their own namespace at the vendored tag: derived, loaded on demand, wiped by a run, never the record. |

The definitions may use a forbidden word once, to name what the term
replaces ("assertion" is defined as a fact, "arm" as an AI assistant):
the table defines, the sentences obey.

## Forbidden synonyms

| do not write | write |
|---|---|
| statement, statements | assertion |
| piece of knowledge, pieces of knowledge | key |
| assistant, assistants | arm |
| artefact, artefacts | document |
| acceptance test, acceptance tests, test suite, the suite | oracle |
| database | store |
| snippet, chunk | fragment |
| register item, register object, element record | node |
| connection, connections, mapping row, edge record | link |
| link type, connection type | relationship type |
| master, golden source, system of truth | source of record |
| an extract, the extract, dump, snapshot | export |
| sign-off, signoff | approval |
| waiver, exemption | exception |
| completeness rule, mandatory mapping | coverage rule |

`FORBIDDEN` in `views.py` holds the same list. Data quoted from the
harness may contain these words (`D3_stale`, "artefact" in a rule hit's
field name): it is data and is shown as it is.

## Terms shared with the IEAM register

The demo shows the vendored IEAM register (`kg_experiment/demo/register/`), whose own
glossary (`register/glossary/glossary.toml`) defines node, link, relationship type, source of
record, export, approval, exception and coverage rule. Those terms are in the table above with
the register's meanings, and their forbidden synonyms in the list, with six reconciliations:

- **extract.** The register forbids it as a synonym of *export*; the demo's pipeline stage is
  *extract* and a basis is *extracted by a parser*. Only the noun phrases "an extract" and
  "the extract" are forbidden here; the stage keeps its name.
- **item, object.** The register forbids them as synonyms of *node*; the demo says "missing
  item" in the gaps sense, and the page's script uses `Object`. Only "register item",
  "register object" and "element record" are forbidden here.
- **ok.** The register forbids it as a synonym of *approval*; the page's script and the CI job
  use `ok` as a field. Not forbidden here; the register's own checker still refuses it in a
  name, a rationale or a decision record.
- **record.** The demo's *record* is the committed results; the register's are always written
  in full as *decision record* and *source of record*.
- **approval.** One term with two objects: an assertion in the store, a node or link in the
  register. A register panel says *node approval* or *link approval* where both are in view.
- **status and state.** An assertion has a *status* (proposed to invalidated); a register node
  or link has a *state* (draft to retired). They never swap.
- **entity and decision.** The demo's *entity* is a thing the documents talk about; the
  register's `ENT` nodes are *information nodes*. The arm's *decision* is its choice; the
  register's is a *decision record*.

The register's names, rationales and finding messages are data on the page, shown as the
register has them.

## What is outside these rules

The harness, its result files and the record
(`docs/neo4j-governed-knowledge-evaluation.md`) keep their own vocabulary;
the rules govern the demo page's generated prose only. The scenario cards
and the Planted line paraphrase the record's §6 table in the approved
terms; the record's own wording is one click away in the record. The README beside
this file is written in the adopter register and follows the glossary's
terms, but is prose, not generated text, and is not checked for length.
