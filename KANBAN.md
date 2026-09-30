# Kanban — DemoCompany Contractor Onboarding

Light Kanban, iterative delivery. Requirement details live in
[requirements.md](requirements.md); decisions and rationale in [intent.md](intent.md).

## Rules
- **Flow:** Backlog → Ready → In Progress → Review → Done
- **WIP limit:** In Progress ≤ 2 cards. Finish before starting.
- **Pull, don't push:** pull the top card from Ready. Backlog order = priority.
- **Review** = Eng. Turing reviews code the engineer wrote. Findings are fixed
  before Done; corrections to AI suggestions go in the AI-usage log (T05).
- **Definition of Done:** code written by the engineer, unit tests pass (where
  the card has testable logic), acceptance examples from requirements.md
  covered, no open review findings, and the engineer can explain every line.
- Only the engineer moves a card to **Done**.
- Card format: `- **ID** Title — note (iteration)`

## Iterations (plan, not commitment)
- **It1 — Walking skeleton:** fetch → naive email → CSV → logs, end to end.
- **It2 — Email core:** full name parsing, character set, uniqueness.
- **It3 — Hardening:** validation, injection, transport, logging discipline, fail-safe.
- **It4 — Deliverables:** README, sample run artifacts, demo prep.

---

## Backlog
- **R06** Name parsing: prefixes, suffixes, initials; < 2 words → skip + log (It2)
- **R09** Username character set: transliterate → lowercase → strip `[^a-z0-9]` (It2)
- **R07** Uniqueness: `jdoe`, `jdoe1`, `jdoe2`… (It2)
- **NR02** Case-insensitive uniqueness as a security property — heaviest test coverage (It2)
- **D01** Decide: empty username after normalization → skip + log? (currently *Proposed*, add to R09) (It2)
- **D02** Decide + record in intent.md: CSV-injection neutralization method (`'` prefix vs strip) and CSV filename (fixed vs timestamped) (It3)
- **NR01** Validate external input; skip + log invalid records by id (It3)
- **NR03** CSV injection neutralization on every cell (It3)
- **NR04** Secure transport: HTTPS, cert verification, timeout, status + content type (It3)
- **NR05** No PII in logs: counts, ids, reasons only (It3)
- **NR06** Fail safely: no partial CSV on error (It3)
- **T02** README: setup, run, assumptions, security considerations, AI-tool disclosure (It4)
- **T03** Commit sample run: generated CSV + execution log (deliverables) (It4)
- **T04** Live demo prep: script, edge cases to show, security talking points (It4)
- **T05** AI-usage log: where suggestions were wrong/corrected (ongoing, closes in It4); ai assist in config.py, fetch.py and test_fetch.py; logging_setup.py and main.py came from ai.


## Ready
- **R08** Logs: start, runtime, fetched, processed, CSV confirmation, validations (It1)

## In Progress
_(WIP ≤ 2)_
- **R02** CSV row per successfully processed contractor, 6 fields; phone as-is string (It1)
- **R01** CSV file generated under `output/` (It1)

## Review

## Done
- **T01** Scaffold: `src/`, `tests/`, `output/`, `.gitignore`, pinned `requirements.txt` for pip (It1)
- **A02** Architecture: low-level design, reviewed (final diagram)
- **A01** Architecture: high-level design, reviewed (v2)
- **S01** Spec review: original brief + real API data checked (2026-09-24)
- **S02** requirements.md: R01–R09, NR01–NR06
- **S03** intent.md: rationale, decisions, open questions; phone format decided
- **R03** Endpoint connection: fetch `/users` JSON — `fetch_users()` raises `FetchError`; logging setup + minimal `main.py` skeleton added; 6 fetch tests (It1)
- **R04** Corporate email generation per contractor (It1)
- **R05** Email format `<initial><lastname>@democompany.com`, lowercase (It1)
- **C01** `Contractor` dataclass + `validate_record()` — presence + type checks; empty strings, lengths, control chars, email format deferred to NR01 (It3) (It1)
