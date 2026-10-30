# 0002 — The pilot slice is the CargoQuote kit, synthetic content only

Date: 2026-10-30. State: approved (fdurieux). Supersedes: none.

## Decision

This repository is a public test case. Its nodes and links describe the CargoQuote kit
(pumllint `kg_experiment/kit`): one product, one journey, four capabilities, one process with
four activities, one application with three modules, four entities. No bank-related data is
stored here; the bank's instance is created from this structure inside the bank's private
repositories and never pushed outside them.

## Why

The IEAM's second step is one business slice. The kit already carries requirements, a decision
table, a specification, an API contract, BPMN, DMN, Gherkin and a `links.toml`, so every link
here has evidence a reader can open.

## Approvals recorded by this decision

Every node and link in the initial commit whose `approval.record` names this file.
