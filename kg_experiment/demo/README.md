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

**A report view** of the selected scenario, in two pictures:

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
  the "no governance" reference.

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
