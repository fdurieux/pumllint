# Runtime pins

These are part of the contract: several stored numbers and printed texts
depend on them (e.g. the `timestamp` resolution in store.md §3, the
`np.float64(...)` repr in the differential report, pandas' `str` dtype for
text columns read back from Parquet).

| item | pin |
|---|---|
| Python | >= 3.11 (the subject runs on CPython 3.12) |
| pandas | ==3.0.5 |
| numpy | ==2.4.6 |
| requests | ==2.34.2 |
| pyarrow | ==25.0.1 |
| package name / version | `jef` 0.6.0 |
| console script | `jef-data` (entry point: the CLI's `main`, which returns the exit code) |
| package data | `universe.toml`, `classifications.toml` shipped inside the package |

Standard-library modules relied on: `tomllib` (TOML parsing and its error
texts), `json`, `hashlib`, `argparse`, `fcntl` (POSIX locking).

The chain needs `bash` (arrays, `[[ ]]`, `pipefail`) and GNU `timeout`.

Revision 2026-10-23 (closing round): the `--help` texts (cli_help.md) and the
parser error lines are Python `argparse` output, and the traceback line of
refusal X-09 is pandas' error text with CPython's name suggestion
(`Did you mean: 'at'?`); both are fixed by these pins (CPython 3.12, pandas
3.0.5) and by an 80-column terminal (`COLUMNS=80`, or none set without a
terminal).
