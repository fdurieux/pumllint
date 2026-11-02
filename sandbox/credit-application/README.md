# Demo sandbox: a credit application, drawn right and drawn wrong

A self-contained demo of pumllint for functional analysts and process
engineers. One business case, a credit application, is drawn as four linked
diagrams, and every diagram exists in two versions:

- **compliant**: the version a reviewer would sign off;
- **non-compliant**: the same diagram with deliberate defects of the kind
  analysts meet every day, such as a decision that does not say which way is
  "yes", a typo that creates a second customer, or a status nothing leads to.

Every one of the eight diagrams renders. The demo shows what pumllint finds
that a picture does not: a browser page draws each diagram next to its
findings, in plain English, with the compliant and non-compliant versions side
by side.

## What you need

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) on a Mac
  (Apple silicon or Intel), Windows or Linux, installed and running.
- [Git](https://git-scm.com/), to get a copy of this repository. On a Mac, the
  first `git` command offers to install Apple's command-line tools if git is
  missing.

Nothing else: Python and pumllint run inside the container.

## Get the repository

The demo lives in the pumllint repository, so you first need a copy of it on
your computer. The first time, *clone* it: this downloads the whole repository
into a new `pumllint` folder.

```bash
git clone https://github.com/fdurieux/pumllint.git
cd pumllint
```

If you already have a copy, *pull* instead. This brings your copy up to date
with the published version, so the demo matches this README.

```bash
cd path/to/pumllint
git checkout main
git pull
```

## The two commands, in plain English

From the repository folder:

```bash
cd sandbox/credit-application
docker compose up
```

`docker compose up` starts two small programs in containers on your own
computer:

- **a PlantUML server**, which turns the diagram text files into pictures;
- **the demo page**, which runs pumllint on both versions of the four diagrams
  and shows the pictures and the findings together.

Then open <http://localhost:8000> in a browser. The first start downloads the
two container images (a few hundred megabytes) and builds the demo image.
After that it works without a network connection, which is useful for a
conference room.

To stop it, press `Ctrl+C` in the terminal, or run `docker compose down`.

After a `git pull` that changed the demo, start it with
`docker compose up --build`, so the demo image is rebuilt with the new
pumllint and page.

## What the page shows

| Diagram | What it is | What is wrong in the non-compliant version |
|---------|-----------|---------------------------------------------|
| `credit-application.puml` | The business process: customer, credit officer and risk engine, as swimlanes | The score decision does not say which branch approves (ACT003, twice), and the process never reaches an end (ACT002, major) |
| `credit-decision.puml` | The decision, as a sequence diagram derived from the process | An `alt` block with no condition, so the reader must guess (SEQ007), and a typo, `Custmer`, that quietly adds a second customer (SEQ001, critical) |
| `credit-scoring.puml` | One step in detail: how the risk engine produces the score | The risk engine is a `<<gateway>>` here and a `<<service>>` in the decision diagram: one system, two descriptions (XD002, reported on both files) |
| `application-status.puml` | The application's status over its life, as a state chart | A status change with no cause (STA003), a status nothing leads to (STA002, major), and no owner named (GEN006) |

The four diagrams are linked as a real set would be. They share participant
and swimlane names, so pumllint can check that the set describes each system
the same way. They also cite the requirement IDs in `requirements.txt`
(CRD-101 to CRD-105), so `pumllint trace` can show which requirement is drawn
where. In the non-compliant set, CRD-105 ("the customer is informed") is drawn
nowhere, and one diagram cites CRD-106, which does not exist.

The verdicts:

- **Compliant set:** no findings, every diagram at Level 4 (Precise), and all
  five requirements covered. The gate passes.
- **Non-compliant set:** ten findings (one critical, two major, seven minor),
  one requirement uncovered, and one unknown reference. The gate fails.

Each non-compliant diagram still scores Level 4. The level says how complete
and precise a drawing is overall; the gate looks at how serious each finding
is, and one critical or major finding is enough to stop a hand-off.

The settings are in `diagrams/lint.toml`: pumllint's defaults plus two house
rules, "every diagram names its owner" and "every diagram cites a CRD
requirement".

## Try it live

The `diagrams/` folder is shared with the container. Open a non-compliant file
in any text editor, fix a defect, save, and reload the page. For example, in
`diagrams/non-compliant/credit-decision.puml`, change the line `alt` to
`alt score sufficient`; the SEQ007 finding disappears. `WALKTHROUGH.md` is a
scripted 15-minute version of the demo.

To put everything back, run `git checkout -- diagrams` from this folder.

## Without Docker

From the repository root, with Python 3.11 or later:

```bash
pip install -e .
python sandbox/credit-application/demo_site.py serve
```

This gives the same findings at <http://localhost:8000>. Without a PlantUML
server the pictures are missing. Point `DEMO_PLANTUML_URL` at one you have
(for example `https://www.plantuml.com/plantuml`) if sending the diagram text
to it is acceptable.

The same checks run from the command line:

```bash
pumllint sandbox/credit-application/diagrams/non-compliant -c sandbox/credit-application/diagrams/lint.toml
pumllint trace sandbox/credit-application/diagrams/non-compliant -c sandbox/credit-application/diagrams/lint.toml \
  --requirements sandbox/credit-application/diagrams/non-compliant/requirements.txt
```

## Kept honest

`tests/test_sandbox_credit_application.py` runs pumllint on both sets on every
change to the repository. It fails if the findings drift from what this README,
the page and the Legible deck's "why it passes or fails" slide say.
