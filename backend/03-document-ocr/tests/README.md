# OCR Tests

**Module:** 03 — Document OCR
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/03-document-ocr/tests`

---

## What this is for

Measure, do not guess. And build the corpus first — everything else here is guesswork without it.

## What it does

- Benchmark on a real labelled corpus
- Notation parsing
- Verification-gate behaviour

## What you build here

| File | Does |
|---|---|
| `test_notation.py` |  |
| `test_tables.py` |  |
| `test_verify_gate.py` |  |
| `corpus/README.md` | how to collect and anonymise 100–300 real documents |
| `corpus/labels.jsonl` | ground truth |
| `benchmark.md` | the table you quote in the pitch |

## Pipeline position

```
IN    the labelled corpus
OUT   accuracy per document type
```

**Depends on:** pytest
**Feeds:** CI + the pitch

## Definition of done

- [ ] **Corpus built in week 1** — 100+ documents, at least 5 prescription styles and 5 lab formats
- [ ] Sources: team members' own family documents (anonymised, with permission) · public sample formats · handwriting the team writes imitating prescriptions
- [ ] **Anonymise before committing.** Never commit a real identifiable patient document.
- [ ] Report separately: printed accuracy · handwriting accuracy · **how often we correctly refused**

## Reference

- `docs/ARCHITECTURE.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*
