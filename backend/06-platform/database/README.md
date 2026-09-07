# Database

**Module:** 06 — Platform
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/06-platform/database`

---

## What this is for

Where everything lives. One schema, owned collectively, migrated in order.

## What it does

- Tables for users, patients, visits, questionnaire answers, documents, extracted entities, summaries, corrections
- Encrypt patient name and phone at the column level
- Append-only audit log

## What you build here

| File | Does |
|---|---|
| `models.py` | all tables |
| `session.py` | engine + session factory |
| `repositories.py` | the query layer — scoping enforced here |
| `migrations/` | alembic, in order |
| `seed.py` | demo patients for testing and the demo |

## Pipeline position

```
IN    module writes
OUT   durable, auditable state
```

**Depends on:** PostgreSQL
**Feeds:** every module

## Definition of done

- [ ] **Ships day 1** — the schema unblocks the other five modules even before their code exists
- [ ] `REVOKE UPDATE, DELETE` on the audit table at the **database** level
- [ ] Patient name and phone encrypted at column level
- [ ] **A patient can only ever read their own rows** — enforced in the repository, not just the route

## Reference

- `docs/DATA_CONTRACTS.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*
