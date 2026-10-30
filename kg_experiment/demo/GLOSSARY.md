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
| controlled | the plain-English block, the stage panels, the gap kinds | 20 words | yes |
| reading | `SCENARIOS[..]["plain"]`, the "what this shows" paragraph | 25 words | yes |
| data | the gate's reason, conflict texts, id lists, engine messages | none | no |

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

`FORBIDDEN` in `views.py` holds the same list. Data quoted from the
harness may contain these words (`D3_stale`, "artefact" in a rule hit's
field name): it is data and is shown as it is.

## What is outside these rules

The harness, its result files and the record
(`docs/neo4j-governed-knowledge-evaluation.md`) keep their own vocabulary;
the rules govern the demo page's generated prose only. The README beside
this file is written in the adopter register and follows the glossary's
terms, but is prose, not generated text, and is not checked for length.
