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
| Name parsing | Ignore prefixes (`Sr.`, `Mr.`, `Mrs.`, `Ms.`, `Miss`, `Dr.`, `Prof.` — `Ms`/`Miss`/`Prof` added 2026-09-30), suffixes (`Jr.`, `Sr.`, `II`–`V`) and single-letter initials. First remaining word = first name, last remaining word = last name. | R06 | Decided |
| Why above | Naive first/last word breaks on real data: `Mrs. Dennis Schulist` → `mschulist`, `Nicholas Runolfsdottir V` → `nv`. | R06 | Evidence |
| Too few words | Fewer than two words remain after stripping (`Dr. Smith`, `John V`) → skip + log. An identity built from half a name is a guess. | R06 | Decided |
| Character set | Username limited to `[a-z0-9]`. Accented Latin characters are transliterated (`Núñez` → `nunez`); separators are stripped (`O'Brien` → `obrien`); characters without a decomposition are stripped. | R09 | Decided |
| Collisions | Case-insensitive; counter per base username; first occurrence gets no number, second gets `1`, third `2`. | R07, NR02 | Decided |
| Bad records | Missing/wrong-typed required field → skip + log reason (by record `id`, not PII). | NR01 | Decided |
| Phone | Kept as a string, passed through as-is (no normalization). Must be a `str` per NR01 and still goes through the NR03 sanitizer like every cell. Rationale: data mixes extensions (`x56442`), `()`, `.`, `-`; no target format is specified; and treating it as a number would drop leading zeros (`010-692-6593`, `024-648-3804`). | NR01, NR03 | Decided |
| Zero valid records | No CSV is written, run exits 1. A provisioning step that produces no identities is a failure, not a success with an empty file. | R01, NR06 | Decided |
| Fetch error contract | `fetch_users()` returns a `list` or raises a single `FetchError` (timeout, connection/TLS failure, HTTP error status, non-JSON body, non-list JSON). `main` catches it, logs one readable line and exits 1 — no raw traceback. Error messages carry the exception type, not `str(e)`, so URLs (which could carry tokens in production) stay out of logs. Chosen over returning `None`, which pushes the check onto every caller and fails later with an unrelated `TypeError`. | R03, NR04, NR06 | Decided |
| Secure transport (NR04) | Non-HTTPS URLs refused before any request is sent (the error names the scheme, never the URL — it could carry credentials). `verify=True` stated explicitly (it is the default; being explicit makes the intent reviewable and greppable). Redirects are **not** followed (`allow_redirects=False`): a redirect could downgrade to HTTP or point to another host, and the endpoint has no reason to redirect. Status must be exactly 200 (3xx and 204 are failures, 4xx/5xx via `raise_for_status`). Content type must be `application/json` (parameters like `charset` allowed). Server-controlled header text is reduced to printable ASCII and truncated before it reaches a message or log (log injection). TLS/cert failures fail closed as `connection failed (SSLError)`. The run logs the source **host** only. Production: a response-size cap via streaming, and certificate pinning or a private CA if the source were internal. | NR04, NR05 | Decided |
| Logging setup | Configured once, in the entry point (`logging_setup.setup_logging()`, called by `main`). Each module uses `logging.getLogger(__name__)`. Console + file handlers; file at `output/DemoCompanyApp.log`, UTF-8, overwritten per run (`mode="w"`) so the committed log is one clean run. Production: append + rotation + retention. | R08, NR05 | Decided |
| Paths | All paths anchored to the project root (`Path(__file__).resolve()`), never the current working directory — output always lands in the fixed `output/` directory. | R01 | Decided |
| Validated record model | `validation.validate_record(raw) -> Contractor` is the trust boundary: raw API dicts never go past it. Validation and construction happen in one function ("parse, don't validate"), so the only way to obtain a `Contractor` is through validation. Built from an allowlist of the 6 fields the CSV needs (`company.name` and `address.city` flattened); every other field is dropped (data minimization). `Contractor` is a frozen dataclass. Checks use `if` + `isinstance`, not `try/except`: a wrong type doesn't always raise, and bad input is expected, not exceptional. `id` must be `int` and not `bool`. Failures raise `InvalidRecordError(record_id, reason)`; reasons name the field, never its value. It1 = presence + type checks. It3 (NR01): id must be ≥ 1; text fields are trimmed and must be non-empty, ≤ 200 chars, and free of Unicode category C characters (control chars incl. tab/CR/LF — also CSV-injection triggers — plus invisible format chars like zero-width spaces and bidi overrides, which make a value display differently than it reads); email must have a plausible shape (one `@`, dot in domain, no whitespace — deliberately not full RFC 5322, it is passed through, not used); duplicate ids within a run are skipped in `main` (ids anchor every log line). Production: a schema library (pydantic) instead of hand-written checks. | NR01, NR05 | Decided |
| CSV output | `csv_writer.write_csv(rows, path)` writes `Row(contractor, corporate_email)` objects. Columns in spec order, Spanish headers (the CSV is the business deliverable for a Spanish-language brief; code and logs stay in English): `Nombre, Telefono, Correo electronico original, Empresa, Ciudad, Correo electronico DemoCompany`. Headers defined once (`CSV_HEADERS`); `_to_cells(row)` is the single function every cell passes through — the hook point for NR03 `sanitize_cell` in It3. Written with `csv.writer` (never string joins), so commas, quotes and line breaks inside values stay in one cell. Opened with `newline=""` (otherwise Windows writes `\r\r\n` → blank lines in Excel) and `encoding="utf-8-sig"`: the BOM makes Excel detect UTF-8 so `Núñez` renders correctly; cost is 3 bytes some non-Excel tools don't expect. Fixed filename `output/external_contractors.csv` for It1 (D02 revisits fixed vs timestamped); path comes only from `config`, never user input. The writer writes what it is given — the "zero valid records → no CSV, exit 1" policy lives in `main`. Direct write for now; temp file + rename is NR06 (It3). | R01, R02, NR03, NR06 | Decided |
| CSV-injection neutralization (D02) | Prefix a single quote `'` to any cell starting with `=`, `+`, `-`, `@`, tab or CR (OWASP's recommended approach), rather than stripping the character. A prefix is visible, consistent and reversible — the original value is still there; stripping silently changes data and can merge into another dangerous character (`==1+1` → `=1+1`). Trade-off: a legitimate leading `-` or `+` (e.g. `+57 300…`) is shown with a `'` in front. Applied to every cell, including generated emails, in `csv_writer._to_cells`. Decided 2026-10-01 by Claude under delegation — **engineer to confirm in review**. | NR03 | Decided |
| CSV filename (D02) | Keep the fixed name `output/external_contractors.csv`, replaced atomically on each successful run (NR06). Matches the per-run log (`mode="w"`) and the deliverable (one committed sample run). Timestamped files would keep history but accumulate files and force the consumer to find "the latest". Production: timestamped file + manifest or run id + retention policy. Decided 2026-10-01 by Claude under delegation — **engineer to confirm in review**. | R01, NR06 | Decided |
| Empty username after normalization | If the first or last name normalizes to `""` (e.g. `李 王`, or a token made only of punctuation) → treat as invalid, skip + log by record id. Same principle as "too few words": an identity built from a guess is not an identity. Also prevents an `IndexError` when taking the initial of an empty string. Decided 2026-09-30 (D01). | R09 | Decided |

### Implementation notes (not requirements, but must hold)
- **Normalization order:** transliterate → lowercase → strip outside `[a-z0-9]`.
  Stripping first would turn `Núñez` into `nez`.
- **Prefix/suffix matching:** case-insensitive, trailing dot optional
  (`Mr` = `Mr.` = `MR.`).
- **Position-aware:** only *leading* prefixes and *trailing* suffixes are
  ignored. `Sr` is in both lists (Señor / Senior); its position decides.
  A prefix-like word in the middle of a name is kept.
- **Initials = a single Latin letter** (`A`, `A.`, `É.`). A one-character
  CJK name part (`李`) is a real name, not an initial; it normalizes to `""`
  and is skipped by D01. Consequence of the rule: `J. R. Tolkien` → only one
  word remains → skipped.
- **Adjustment logging:** `parse_name` reports *categories* ignored
  (`prefix`, `suffix`, `initial`), never the tokens; `main` logs
  `record <id>: name adjusted (<categories> ignored)`.
- **Collision handling (R07):** `EmailRegistry.assign(base)` keeps a per-base
  counter *and* checks every candidate against all usernames issued in the
  run. The counter alone is not enough: base `jdoe` + suffix `1` and base
  `jdoe1` (a name like `John Doe1` — digits are allowed by R09) are the same
  string. One registry per run (`main`); logged as
  `record <id>: email collision resolved, suffix <n> assigned` — never the
  username, which is derived from the name.
- **Homoglyphs:** NFKD folds compatibility forms (fullwidth `Ｊ` → `J`), but a
  Cyrillic `а` has no decomposition and is stripped — a lookalike name yields
  a *different* username (`jne`), never the Latin original's.
- **Known limitation:** Unicode NFKD handles `ñ`, `ú`, `é` but not `ł`, `ø`,
  `ß`, `æ` (`Łukasz` → `ukasz`). Documented, not fixed — production would use a
  dedicated transliteration library.
- **Known limitation:** validation reasons use the bare key name, so a failure
  on `company.name` reads `missing required key: name`, identical to a failure
  on the contractor's own `name`. Accepted for It1: the record id is still
  logged and the record is correctly skipped; only the log message is
  ambiguous. Fix if needed: pass a dotted path (`company.name`) to `_require`
  for the message.

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
- Up to R01/R02 (It1): Claude (Eng. Turing) reviewed, challenged, and
  explained; the engineer wrote the core logic (email generation, validation,
  CSV writing). Exceptions are recorded in T05.
- From R08 onward (decided 2026-09-30): the engineer specifies and requests
  code; Claude writes it; the engineer reviews, questions and approves every
  change before commit, and must be able to justify every line in the demo.
  Design decisions remain the engineer's.
- Keep a short log of places where suggested code was wrong or was corrected —
  it is direct evidence for the demo.
- Disclose tool usage openly in the README.

## Open questions (can be emailed to the recruiter — the brief invites it)
1. Should collision uniqueness consider only this run, or pre-existing accounts?
2. Honorifics/suffixes: is stripping them the expected behavior?
3. Any expected phone format in the CSV?
