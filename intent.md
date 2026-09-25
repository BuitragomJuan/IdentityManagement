# Intent — DemoCompany Contractor Onboarding

> **Source of truth for *what* the system does:** [requirements.md](requirements.md)
> (R01–R09 functional, NR01–NR06 security). This document captures *why*,
> the decisions behind those requirements, and what is still open.

## Why this exists
DemoCompany needs to give external contractors (supplied by partner companies)
access to its corporate services. Their data arrives from an external source
with non-corporate emails. This tool is the first step of that onboarding:
it pulls contractor records, derives a unique corporate email for each, and
produces an auditable CSV + execution log.

It is an **identity provisioning step**. Treat it like one: the output
(identities) must be unique, deterministic, traceable, and must not be a
vector for harm to whoever consumes it downstream.

## Success criteria
The run is successful when:
1. Every valid record from `GET /users` produces exactly one CSV row with:
   full name, phone, original email, company, city, generated corporate email.
   *(R01, R02, R03)*
2. Generated emails follow `<first initial><last name>@democompany.com`,
   lowercase, only `[a-z0-9]` in the username. *(R04, R05, R06, R09)*
3. Generated emails are **unique** across the run, case-insensitive
   (`jdoe`, `jdoe1`, `jdoe2`, ...). *(R07, NR02)*
4. Invalid records are skipped with a logged reason, never crash the batch.
   *(NR01, R06)*
5. The log shows: process start, runtime, records fetched, records processed
   successfully, CSV generation confirmation, relevant validations. *(R08)*
6. A failed run leaves no partial CSV behind. *(NR06)*
7. Same input → same output (deterministic; ordering follows API order).

## Deliverables (from the brief)
- Source code
- **The generated CSV** — must be committed to the repo, not gitignored
- **Execution log evidence** — same, commit a sample run's log
- Live demo — the engineer must be able to run and explain it end-to-end

## Non-goals
- No actual account creation in any directory (AD/LDAP/Entra) — CSV only.
- No persistence across runs: uniqueness is per run, not against an existing
  directory of already-issued emails. *(Production would check the real
  directory; call this out in the interview.)*
- No UI, no scheduling, no auth (endpoint is public).

## Decisions & assumptions
Validated against the real API data on 2026-09-24 (10 records).

| Topic | Decision | Req | Status |
|---|---|---|---|
| Name parsing | Ignore prefixes (`Sr.`, `Mr.`, `Dr.`, `Mrs.`), suffixes (`Jr.`, `Sr.`, `II`–`V`) and single-letter initials. First remaining word = first name, last remaining word = last name. | R06 | Decided |
| Why above | Naive first/last word breaks on real data: `Mrs. Dennis Schulist` → `mschulist`, `Nicholas Runolfsdottir V` → `nv`. | R06 | Evidence |
| Too few words | Fewer than two words remain after stripping (`Dr. Smith`, `John V`) → skip + log. An identity built from half a name is a guess. | R06 | Decided |
| Character set | Username limited to `[a-z0-9]`. Accented Latin characters are transliterated (`Núñez` → `nunez`); separators are stripped (`O'Brien` → `obrien`); characters without a decomposition are stripped. | R09 | Decided |
| Collisions | Case-insensitive; counter per base username; first occurrence gets no number, second gets `1`, third `2`. | R07, NR02 | Decided |
| Bad records | Missing/wrong-typed required field → skip + log reason (by record `id`, not PII). | NR01 | Decided |
| Phone | Kept as a string, passed through as-is (no normalization). Must be a `str` per NR01 and still goes through the NR03 sanitizer like every cell. Rationale: data mixes extensions (`x56442`), `()`, `.`, `-`; no target format is specified; and treating it as a number would drop leading zeros (`010-692-6593`, `024-648-3804`). | NR01, NR03 | Decided |
| Empty username after normalization | e.g. a name with no Latin letters strips to `""` → treat as invalid, skip + log. Not yet explicit in R09. | R09 | **Proposed** |

### Implementation notes (not requirements, but must hold)
- **Normalization order:** transliterate → lowercase → strip outside `[a-z0-9]`.
  Stripping first would turn `Núñez` into `nez`.
- **Prefix/suffix matching:** case-insensitive, trailing dot optional
  (`Mr` = `Mr.` = `MR.`).
- **Known limitation:** Unicode NFKD handles `ñ`, `ú`, `é` but not `ł`, `ø`,
  `ß`, `æ` (`Łukasz` → `ukasz`). Documented, not fixed — production would use a
  dedicated transliteration library.

## Security intent
Target role is IT Security Junior Consultant — this section is evaluated, not decorative.
Formal requirements live in requirements.md; this is the reasoning behind them.

- **Untrusted input (NR01):** the API is an external source. Validate shape and
  types before use; never assume a field exists.
- **Identity uniqueness is a security property (NR02):** two people sharing one
  corporate mailbox = access-control failure. Collision handling gets the
  heaviest test coverage.
- **CSV / formula injection (NR03):** neutralize cells starting with `=`, `+`,
  `-`, `@`, tab or CR. Trade-off: a leading `-` can be legitimate data, so the
  neutralization must be applied consistently and documented, not silently
  corrupt values.
- **Secure transport (NR04):** HTTPS only, certificate verification on,
  explicit timeout, status code and content type checked; fail with a readable
  log line (no raw stack trace in the output log).
- **Logging discipline (NR05):** log counts, record ids, and reasons — not full
  names, phones or emails.
- **Fail safely (NR06):** no half-written CSV — a partial file can still be
  picked up and used to provision access.
- **Not formalized as requirements (kept as practice):**
  - File I/O: write only under a fixed `output/` directory; no user-controlled paths.
  - Dependencies: `requests` pinned; stdlib otherwise.

## AI-assistance & authorship
The brief states the live demo will cover which assistance tools were used, and
that the evaluation includes **the ability to validate and correct externally
generated output, with the final logic being the candidate's own**.

Working rule for this project:
- Claude (Eng. Turing) reviews, challenges, and explains; the engineer writes
  or deliberately rewrites the core logic (email generation, validation,
  sanitization) and can justify every line.
- Keep a short log of places where suggested code was wrong or was corrected —
  it is direct evidence for the demo.
- Disclose tool usage openly in the README.

## Open questions (can be emailed to the recruiter — the brief invites it)
1. Should collision uniqueness consider only this run, or pre-existing accounts?
2. Honorifics/suffixes: is stripping them the expected behavior?
3. Any expected phone format in the CSV?
