# Security policy

## Reporting a vulnerability

Please report suspected vulnerabilities privately — do not open a public
issue:

- **Preferred:** GitHub private vulnerability reporting — *Security →
  Report a vulnerability* on this repository (if the form is unavailable,
  use email).
- **Email:** fdurieux@i-kei.com

This is a single-maintainer project: expect an acknowledgement within a
week, best-effort. Please include a reproduction (input file, config,
command line) where possible.

## Supported versions

Only the latest release on PyPI receives fixes. pumllint is pre-1.0; there
are no maintenance branches.

## Scope and trust model

In scope: the `pumllint` package as shipped on PyPI, the composite GitHub
Action (`action.yml`), and the pre-commit hooks. The `tools/` directory
holds development-only experiment harnesses and is not part of the shipped
package.

Known, intentional trust boundary — not a vulnerability: **the
configuration file carries code-level trust.** `scoring.syntax_command`
names a command pumllint executes for the opt-in syntax gate, so a
pumllint config is to be trusted like a Makefile or pre-commit config;
do not run pumllint with an auto-detected config inside a checkout you
do not trust.

A full assessment of the codebase's security posture (threat model,
findings, and hardening measures deliberately not taken) is kept in
[docs/security-hardening-assessment.md](docs/security-hardening-assessment.md).
