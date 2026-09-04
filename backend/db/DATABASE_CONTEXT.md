# DATABASE MODULE

**Owner:** Member 6 (M6) · table designs proposed by each module owner
**Stack:** PostgreSQL 16 · SQLAlchemy 2.x · Alembic
**Deep spec:** [`docs/06-M6-platform-core.md`](../../docs/06-M6-platform-core.md) §5

---

## Why this is its own module

Every module writes clinical or legal data. If the schema is inconsistent, the summary is wrong
and the audit trail is worthless. One person owns the migration chain; module owners propose
tables and own their repositories.

---

## Layout

```
db/
├── session.py          engine + session factory
├── base.py             declarative base
├── models/             SQLAlchemy tables
├── repositories/       query layer, one per module
├── migrations/         alembic
│   └── versions/       001_core .. 005_platform
└── seed/               the three demo scenarios + loader
```

---

## Tables by owner

| File | Tables | Proposed by |
|---|---|---|
| `models/patient.py` | `patients` (name/phone encrypted at column level) | M1 |
| `models/session.py` | `sessions` | M1 |
| `models/consent.py` | `consents` — immutable, `supersedes` chain | M1 |
| `models/audit.py` | `audit_log` — **append only** | M1 |
| `models/outbox.py` | `fhir_outbox` | M1 |
| `models/slot.py` | `slots`, `interview_state`, `red_flag_events` | M3 |
| `models/document.py` | `documents`, `doc_entities`, `ocr_training_pairs` | M4 |
| `models/summary.py` | `summaries`, `provenance`, `corrections`, `prakriti_scores` | M5 |
| `models/guardian.py` | `guardian_log` — **append only** | M5 |
| `models/alert.py` | `alerts` | M6 |
| `models/triage.py` | `triage_queue` | M6 |

---

## Migration chain

```
001_core.py           patients · sessions · consents · audit_log
002_conversation.py   slots · interview_state · red_flag_events
003_documents.py      documents · doc_entities · ocr_training_pairs
004_summary.py        summaries · provenance · corrections · guardian_log · prakriti_scores
005_platform.py       triage_queue · jobs · fhir_outbox · metrics_rollup
```

All five ship on **day 1**, even though the code that fills them does not exist yet.
That is what lets five people start.

---

## Rules

1. **`audit_log` and `guardian_log` reject UPDATE and DELETE at the database level.**
   `REVOKE UPDATE, DELETE ... ` in the migration. Not a convention — a grant.
2. **Every patient-data table has `session_id` indexed.**
3. **`patients.name` and `patients.phone` are encrypted at the column level.** If someone dumps
   the DB, demographics must not be readable.
4. **Postgres holds only committed, consented data.** In-flight session state lives in the
   Redis vault with a TTL, so "cleared immediately after submission" is structural, not a cron job.
5. **Every migration is reversible**, or explicitly marked irreversible with a reason.
6. Repositories return **contract objects**, never raw ORM rows, across a module boundary.

---

## Seed data

`seed/` holds the three demo scenarios. They are simultaneously the mock fixtures, the
integration-test data, and the demo script. **Write them properly once.**

```
fixtures_normal_fever.json      12-question path, LOW risk, clean summary
fixtures_cardiac_redflag.json   aborts at question 6, alert emitted, partial slots kept
fixtures_ayush_return.json      full Dashavidha, delta summary, dual-coded Prakriti
```

```bash
python -m backend.db.seed.seed --scenario all
```
