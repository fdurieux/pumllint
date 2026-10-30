# The governed-repository demo

A small web application and a Neo4j database, started together with one
command, that let you walk through the proof of concept recorded in
[`docs/neo4j-governed-knowledge-evaluation.md`](../../docs/neo4j-governed-knowledge-evaluation.md)
(2026-10-30, pull requests #214 to #218): a specification kit loaded into
a graph database as *assertions* (one statement each, with where it came
from, how it was obtained and whether anyone has verified it), seven
checking rules, a *gate* that decides whether an AI coding assistant may
build from that knowledge, and a comparison of two assistants on seven
planted situations: one that receives the gate's verdict and evidence
(the *governed arm*, G), one that receives the documents only (the
*baseline arm*, B). Every result shown is already committed to this
repository; the demo works offline from the first start.

## What you see

**A menu** of the seven scenarios S1 to S7 (complete, missing, ambiguous,
contradictory, inferred, invalidated by a change, unverified), each with
three buttons.

**A report view** of the selected scenario. It opens with *In plain English*,
a few sentences written from the same result files that say what was
planted, what the store found, what the gate's verdict means, what each
arm did and what that shows, and, for a re-run, whether its numbers
match the record. Those sentences, the stage panels and the gap kinds use
one word per concept and keep to 20 words a sentence; the words are
defined in a *Glossary* card under the block and in
[`GLOSSARY.md`](GLOSSARY.md), and a test holds the page to both. Then two pictures, the first of them clickable, every
box of the pipeline opening a panel with that stage's full data (the
documents read, the constraint attempts, each rule's hits, the 36 keys
with their levels, each run's decision and grade). A *gaps* box beside the
rules opens every gap of the scenario grouped by kind, with a filter and a
plain-English sentence per kind; it reads the result files, and the
running Neo4j as well when the scenario on screen is the one loaded there:

- the *pipeline*, from reading the files to grading the generated code,
  each stage coloured by its outcome and carrying its numbers: how many
  fragments and assertions were read, what the rules found, the gate's
  verdict and the keys that blocked it, and, for each arm, what the
  assistant decided, whether it wrote code, whether it raised the planted
  problem, and how its code scored on the kit's eleven acceptance
  scenarios;
- the *systemic model*, the reduced "knowledge view" of the Legible impact
  model (version 0.3, vendored under `model/`), with the scenario's defect
  placed where it entered and the path it travelled, side by side for the
  governed arm and the baseline, with the degradation test's numbers as
  the "no governance" reference. Each box of the model is clickable: the
  panel gives the model's definition of the node and its edges, what the
  record's reading placed there for each arm, and the evidence from the
  result files that bears on it (the gaps for an upstream defect, the
  arms' assumptions for an unresolved decision, the oracle's results for
  the code, the invalidated assertions for drift).

Below the pictures: the evidence bundle the governed arm received, the
generated code of every run, the oracle's verdict per acceptance scenario
and per run, and the questions and assumptions each run returned.

**The store itself.** A link opens Neo4j Browser on the running database
(user `neo4j`, the password you set), and a box of saved queries lets you
ask it directly: the three-valued answer (asserted, documented absent,
unknown), the chain from a changed fragment to the code built on it, the
contradiction pairs, the gap census. The free edition of Neo4j serves one
database, so the store holds the scenario loaded last; the header says
which.

**The register.** The last entry of the Scenarios list is the IEAM
register, a separate public repository
([fdurieux/ieam-register](https://github.com/fdurieux/ieam-register))
that keeps the identities, typed relationships and approvals of the same
CargoQuote kit the scenarios use. Its card gives the commit the demo
carries (`register/SOURCE.md` says which), the counts and the register's
own coverage figures; *Open* replaces the scenario report with the
register in the wide column: its exception and mapping matrix,
the nodes by taxonomy (clicking one opens a panel with its state, owner,
approval, source of record and the links in and out), the relationship
types with their ARIS and Archi status, and an *Impact* box that answers
the IEAM's own question: type a node id (the QuoteAPI module is the
default) and the register's walk shows every link it follows to the
processes, products and journey steps retiring that node would touch,
with each link's state, owner and evidence. The walk follows links only
and does not climb a node's parent, so it says so when it reaches no
product. A link runs the checker at today's date instead of the pinned
one, so you can see an exception expire. Clicking a scenario brings the
report back. Nothing on the page is written back to the register.

## What Neo4j holds, who writes it and who reads it

The store is a graph: things as nodes, relationships between them as
edges. Written from the harness code and the record, for a reader who
knows software but none of this project's shorthand.

### What Neo4j holds

For one loaded scenario the store holds these kinds of things.

- **Documents and their versions.** Each input file of the CargoQuote kit
  (requirements, decision tables, BPMN process, DMN table, diagrams,
  Gherkin scenarios, OpenAPI file, link set) is a document node named by
  its path, with one version node per ingestion carrying the whole file's
  digest (a fingerprint of its bytes) and a pointer to the current version.
- **Fragments.** A version is cut into pieces (a table row, a note, a
  process step, a scenario), each stored with where it sits in the file,
  its own digest, and a copy of its text so evidence can be quoted later.
- **Entities.** The things the kit talks about (a decision-table row, a
  pricing step, a requirement, the API), each with a declared identifier.
- **Assertions.** One statement each: an entity, a property, a value (for
  example, the surcharge of pricing step P2 is 316.00). Each carries a
  *basis* (how it came to exist: authored by a human, extracted by a
  deterministic parser, or inferred by a model) and a *status* (where it
  is in its lifecycle: proposed, validated, verified, approved, disputed,
  invalidated), and points at the fragment that supports it.
- **Provenance.** The activity that produced each assertion (an extraction
  run, with a timestamp) and the agent behind it: the harness as a tool,
  the maintainer as a human, or the architecture assistant as a model.
- **Verification records.** Each says that one assertion was checked, by
  which method (running the kit's test suite, with the digest of the code
  it ran against, or a dated human review), with a scope and, once a later
  change ends it, a valid-until marker.
- **Approvals.** The maintainer's recorded acceptance of a verified
  assertion, naming the written record it rests on.
- **Gaps.** Things found wanting: knowledge declared missing in the
  documents, vague wording, a contradiction, or an assertion nobody
  verified.
- **Conflict edges** joining two assertions that give different values for
  the same property.
- **Derived outputs.** The identity and digest of a piece of generated
  code, with edges to every assertion it used, and a flag that turns on if
  any of those is later invalidated.

What is not there: the documents' content stays in git, and the model's
prompts, replies and generated code land in result files on disk. The
store keeps fragment copies for quoting and the digests that prove which
bytes they were; it is authoritative for status, provenance and links,
never for content.

### Who writes, and when

Only the harness writes, and always in the same order for each scenario.
It first deletes everything in the store. It then applies constraints
(uniqueness of identifiers; six are accepted, and three the free edition
cannot enforce are refused, which is itself a recorded measurement). It
loads the kit: documents, versions, fragments, entities, and every
assertion at status *proposed*, each tied to its extraction activity and
agent. It loads verifications and approvals, matching the kit's test
scenarios to the statements they exercise and the maintainer's dated
review to the rest, which moves matched assertions to *verified* and then
*approved*. Scenario S5 also adds one model-proposed assertion, attributed
to the model and linked to the open decision it claims to fill. Then the
seven rules run: one checks the graph's structure and only reports; the
others promote agreeing statements from different documents to
*validated*, mark contradicting pairs *disputed* and add conflict gaps,
and raise gaps for vague wording, for declared or undetectable missing
knowledge, and for unverified statements.

S6 has a second stage. The generated code from S1 is registered as a
derived output pointing at its assertions. The changed decision table is
re-ingested as version two; unchanged fragments are recognised by digest
and reused, so only the changed rows produce new assertions. The
staleness rule then invalidates every older assertion whose supporting
fragment changed, ends its verifications and flags the derived code
suspect. Finally a re-verification and re-approval are recorded for the
three new statements, and the other new assertions are re-verified
against the known-good values.

The model arms never write to the store; their output goes to files.

### Who reads, and what comes out

The gate reads for the coding task. For each of its 36 required pieces of
knowledge (such as the weight bounds, each screening row's behaviour, the
pricing steps, the response vocabulary) it fetches the live assertions
with their quoted fragment text, verifications, approvals, gaps and
originating agent, plus any declared gap on that key. It computes a level
per key (the weakest status among its assertions, or *absent* if there is
none, or *declared gap*), flags for ambiguity or model-inferred basis, and
a verdict: BLOCKED if any key is absent, a declared gap, disputed or
invalidated, or if more than a quarter are below verified; QUALIFIED if
some are below verified or flagged; otherwise PROCEED. It also reads the
conflict gaps, the invalidated assertions with their ended verifications
and successors, and suspect derived outputs. All of it is rendered as a
text bundle: verdict, policy, then key by key. The governed arm receives
that bundle; the baseline arm receives the documents themselves and never
sees the store.

The demo reads a small census: which scenario is loaded, assertions by
status, node and edge counts. Its saved queries, pasted into Neo4j
Browser, answer: which scenario is loaded; the three-valued answer; the
gate's view of one key; the chain from a changed fragment to invalidated
assertions, ended verifications, successors and the derived code; the
contradiction pairs; the gap census; the status census.

The three-valued answer is the thing a document search cannot give:
*asserted* (a value is stated), *documented absent* (every statement says
there is none), or *unknown* (no statement exists at all). A search
returning nothing cannot tell the last two apart.

### What the store adds that files alone cannot

Status and provenance become data you can query, not something a reader
infers from prose. A change to one fragment can be followed as a
traversal: fragment to the statements it supports, to their
verifications, to the code built on them, giving a deterministic list of
what must be re-checked. Two documents stating different values become an
explicit disputed pair rather than a discrepancy someone might notice.
The free Community edition serves one database, so the store holds one
scenario at a time, the demo runs one load at a time, and the header says
which scenario is loaded.

### What the store does not do

The governance is application logic: the seven rules and the gate are
Python issuing graph queries, and nothing in Neo4j would promote, block or
invalidate on its own. The store supplies storage, uniqueness of
identifiers and traversal; it cannot even require that every assertion
carries a status on this edition, so that check too falls to the
application.

## The three modes, and what each costs

| mode | what happens | needs | time | cost |
|---|---|---|---|---|
| **Replay** | shows the committed results of that scenario | nothing | instant | none |
| **Deterministic** | re-runs the loading, the rules and the gate (measures D1 to D6) against the demo's own Neo4j, then shows the fresh numbers next to the record's | the database container (started with the app) | about five seconds | none; no network |
| **Arms** | re-runs the two assistants once each (`--n 1`; the record used five runs) against the freshly loaded store, grades them with the kit's oracle, shows the result | an OpenAI API key in `OPENAI_API_KEY` | one to two minutes | a few cents per scenario at the recorded model's list price |

The Arms button stays greyed out until the key is set. A re-run of either
kind writes into a dated folder, `kg_experiment/results/demo-runs/<date-time>/`,
and never into `kg_experiment/results/`, which is the published record.
The report view lets you switch between the record and any demo run.

## Which model the Arms mode calls

The record's two arms were answered by `gpt-5.1-2025-11-13`, and the
demo calls that model by default, so an Arms run is like-for-like with
the record. That model is a year old, and on a new OpenAI organisation
its rate limit can be as low as 10,000 tokens per minute, while the
governed arm's prompt alone is about 15,000 tokens: the call is then
refused with a 429 "request too large" before it runs, and the page says
so in red. Two ways out, and the page lets you switch between them at
any time:

- **Raise the limit** on the OpenAI side (a higher usage tier, or a
  limit-increase request on your organisation's Limits page) and keep
  the record's model. Results stay comparable with the record.
- **Call another model**, chosen in the *Arms call* toggle at the top of
  the scenario list (default `gpt-5.5`). The gate, the evidence bundle
  and the oracle are unchanged, but the arms' answers are another
  model's: the page marks every such run in red as a deviation, names
  the model on each run, and the numbers are not comparable with the
  record's. Setting `KG_ARMS_MODEL` in the environment before
  `docker compose up` preselects this choice.

The choice is remembered by your browser. Either way a re-run writes
into `results/demo-runs/`, never into the record, and the cost estimate
the harness prints uses the record model's list price.

## Quick start on a Mac, step by step

Six steps. Each block is ready to paste into Terminal (zsh) as a whole;
the line above each says what it does.

**1. Prerequisites.** Install
[Docker Desktop](https://www.docker.com/products/docker-desktop/) if you
do not have it, start it, and wait until its menu-bar icon says it is
running. `git` comes with macOS (it offers to install the command-line
tools the first time you type it). Then check the engine answers:

```bash
docker info >/dev/null 2>&1 && echo "docker engine running" || echo "docker engine NOT running: start Docker Desktop"
```

**2. Set the OpenAI key, only if you want the Arms mode.** Paste this
with your real key in place of the placeholder. The variable lives in
this Terminal window only; it is never written to disk and never baked
into the image. Skip this step and the Arms buttons simply stay greyed
out; Replay and Deterministic work without it.

```bash
export OPENAI_API_KEY=sk-your-real-key-here
```

Optionally choose a database password other than the default
`kgpoc2026`:

```bash
export KG_NEO4J_PASSWORD=choose-a-password
```

**3. Clone and start the stack.** Paste the whole block at once. It
checks the tools and says what to install if one is missing, clones the
repository into your home folder (or updates it if it is already there),
sets the two variables the stack reads, builds the application image,
pulls the Neo4j image, waits until both containers are healthy, prints
the two addresses, and opens the demo in your browser.

```bash
set -e
command -v git >/dev/null 2>&1 || { echo "git is not installed. Run: xcode-select --install"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "docker is not installed. Install Docker Desktop from https://www.docker.com/products/docker-desktop/"; exit 1; }
docker info >/dev/null 2>&1 || { echo "the docker engine is not running. Start Docker Desktop and wait for it to say it is running, then paste again"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "docker compose is missing. Update Docker Desktop"; exit 1; }
cd "$HOME"
if [ -d pumllint/.git ]; then cd pumllint && git pull --ff-only; else git clone https://github.com/fdurieux/pumllint.git && cd pumllint; fi
export KG_NEO4J_PASSWORD="${KG_NEO4J_PASSWORD:-kgpoc2026}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"
cd kg_experiment/demo
docker compose up -d --build --wait --wait-timeout 300
echo "demo:          http://localhost:8080"
echo "Neo4j Browser: http://localhost:7474  user neo4j, password $KG_NEO4J_PASSWORD"
open http://localhost:8080
```

The first start takes a minute or two (the image build plus the Neo4j
pull). Later starts take seconds.

**4. Use it.** In the browser at `http://localhost:8080`:

- the two chips in the header say whether the store is reachable and
  whether the Arms mode is enabled;
- click a scenario card to **Replay** its recorded results;
- click **Deterministic** to re-run D1 to D6 against the container's
  Neo4j (about five seconds); the run's log appears on the left, and the
  view switches to the new demo run when it finishes;
- click **Arms** (needs the key) to re-run both model arms once; one to
  two minutes, a few cents;
- use the **source** dropdown in the report header to switch between the
  record, S6's re-run, and any demo run;
- **Open Neo4j Browser** opens `http://localhost:7474` on the scenario
  loaded last; log in as `neo4j` with your password and paste any saved
  query from the left panel.

Re-runs land in `~/pumllint/kg_experiment/results/demo-runs/<date-time>/`,
which git ignores.

**5. Stop it.**

```bash
cd "$HOME/pumllint/kg_experiment/demo" && docker compose down
```

Add `-v` to that command to delete the Neo4j data volume as well; the
demo runs stay, because they are in your checkout.

**6. Restart later.** A new Terminal window has forgotten the key, so
export it again first if you want the Arms mode:

```bash
export OPENAI_API_KEY=sk-your-real-key-here
```

```bash
cd "$HOME/pumllint/kg_experiment/demo" && git pull --ff-only && docker compose up -d --build --wait && open http://localhost:8080
```

Two cautions. Never commit the key or put it in a `.env` file you might
push. And if you ever run this on a server (see the EC2 route below),
restrict the firewall to your own address on ports 8080, 7474 and 7687:
the demo page has no login, and 7474 is a live database console.

### What the start block does, in plain English

The first four lines check that `git`, `docker` and `docker compose` are
present and that the Docker engine is running; each stops with a message
naming the fix. The next two lines go to your home folder and clone the
repository, or update it if it is already there. The two `export` lines
set the two variables the stack reads: the database password (the
harness's default if you have not chosen one) and the OpenAI key (kept
empty when you have not exported one, which disables the Arms mode). The
last lines start both containers, wait for their health checks, print the
two addresses, and open the demo.

## Start it elsewhere

**Another laptop, without building.** The compose file names the image
the repository publishes on every merge, `ghcr.io/fdurieux/pumllint-kg-demo:latest`
(also tagged with the commit's short SHA). From the `kg_experiment/demo`
directory of a checkout:

```bash
docker compose -f docker-compose.yml pull
```

```bash
docker compose -f docker-compose.yml up -d --wait
```

Naming the compose file explicitly skips the development override, which
would otherwise build the image locally. If the pull is refused, the
package is private on GitHub: log in with `docker login ghcr.io` using a
token that can read packages, or ask the repository owner to make the
package public. Demo runs then live in a Docker volume named
`pumllint-kg-demo_demo-runs`; `docker compose down -v` deletes them.

**An EC2 instance.** A `t3.medium` (two vCPUs, 4 GB) is enough: Neo4j is
configured for 1 GB of heap and 512 MB of page cache, the app needs little.
Use an Ubuntu image with Docker installed, clone the repository, and start
the stack as above with `KG_BROWSER_URL=http://<the instance's public address>:7474`
exported so the demo's "Open Neo4j Browser" link points at the instance
rather than at your own machine. **Restrict the security group to your own
IP address** for ports 8080, 7474 and 7687: the demo page has no
authentication at all, and port 7474 is a live database console protected
only by the password you set. Do not leave the instance reachable from the
internet; stop or terminate it after the session.

**The OpenAI key.** It is read from the environment of the shell that
starts the stack and passed into the application container only. It is
never written to disk, never baked into the image, and never sent
anywhere but to the OpenAI API by the harness's own calls. Without it the
Arms mode is simply disabled; everything else works.

## Files

| path | what |
|---|---|
| `docker-compose.yml` | the two services, with the registry image for the app |
| `docker-compose.override.yml` | local build of the app image from this checkout, and demo runs written into the checkout |
| `Dockerfile`, `Dockerfile.dockerignore` | the app image: Python 3.13, this repository installed, the harness's dependencies at the record's versions |
| `app/server.py` | the web server (standard library only): the menu, the report view, starting a re-run, the store's status |
| `app/views.py` | builds the report view of a scenario from its result files |
| `app/cascade.py` | draws the systemic-model view with the deck generator's layout |
| `app/index.html` | the one page |
| `model/model.json`, `model/SOURCE.md` | the vendored Legible model v0.3 and where it came from |
| `tools/compare_deterministic.py` | compares a deterministic run against the record, field by field; the CI job and the pull request's proof use it |
