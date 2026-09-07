# Migrations

**All migrations ship on day 1**, even though the code that fills the tables does not exist yet.
That is what lets the other five modules be built in parallel.

```
001_users.py        users · sessions · verification tokens
002_patients.py     patients · visits
003_questionnaire.py  questions asked · answers · audio refs · emergency flags
004_documents.py    documents · extracted entities · verify queue
005_summary.py      summaries · sources · doctor corrections
006_audit.py        audit log — APPEND ONLY
```

- [ ] Every migration is reversible, or explicitly marked irreversible with a reason
- [ ] The `REVOKE UPDATE, DELETE` on the audit table lives **in the migration**
- [ ] Never edit a migration already applied on someone else's machine — add a new one

```bash
make migrate
```
