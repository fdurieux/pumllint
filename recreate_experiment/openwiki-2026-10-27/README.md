# OpenWiki against the kit (opened 2026-10-27)

A pre-registered comparison of LangChain's OpenWiki generated wiki with this
programme's specification kit, on the same clean-room subject (J-F's daily
asset load at `8f6d6b0`). Read `PREREGISTRATION.md` first; its §5 is the
order of work and its Results section is the record.

| path | what |
|---|---|
| `PREREGISTRATION.md` | question, arms, measures M1–M9, expectations H1–H7, bounds; Results appended below the line |
| `tools/make_clean_room.py` | builds the subject tree from a J-F checkout and makes it a one-commit git repository; prints the subject hash |
| `tools/run_openwiki.sh` | generates Arm W non-interactively with the pinned OpenWiki, records `PROVENANCE.json` and `run.log` |
| `tools/claims_worksheet.py`, `tools/claims_tally.py` | M1: the seeded claims sample as a worksheet, and its tally |
| `tools/coverage_worksheet.py`, `tools/coverage_tally.py` | M2: the 163 requirements as a worksheet, and its tally by kind |
| `results/<arm>/` | the artefact as generated, the graded worksheets, the provenance; absent until the arm runs |

The tools were dry-run on OpenWiki's own wiki (748 claims on 22 pages at
its HEAD `305599f`) to prove the sidecar parser; nothing from that dry run
is a result here.
