# Lab Reports

**Module:** 03 — Document OCR
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/03-document-ocr/lab_report`

---

## What this is for

Printed, structured, and immediately useful to a doctor. **This is our strongest OCR demo — lead with it.** The critical requirement is preserving the relation between the test name, its value, its unit and its reference range.

## What it does

- Detect the table structure and the cell grid
- Map columns even though every lab uses different headers
- Extract test · value · unit · reference range
- Flag anything outside the reference range, with direction

## What you build here

| File | Does |
|---|---|
| `tables.py` | table detection → rows |
| `headers.py` | synonyms: Result / Value / Observed · Ref Range / Normal Range / Biological Ref Interval |
| `parse.py` | one row → one structured result |
| `ranges.py` | fallback reference ranges when the report omits them |
| `flag.py` | ↑ above range · ↓ below range |

## Pipeline position

```
IN    a lab report page
OUT   structured results with abnormal flags
```

**Depends on:** a printed-OCR engine with table support
**Feeds:** module 04, doctor portal reports section

## Definition of done

- [ ] **test ↔ value ↔ unit ↔ range stays linked** on real lab formats — a value with no test name is useless
- [ ] Missing reference range falls back to a built-in table, and records which source was used
- [ ] Output reads like: `Hemoglobin 10.2 g/dL ↓ below reference (12–16)`
- [ ] Multiple reports of the same test across dates produce a **trend**, not two isolated numbers

## Reference

- `docs/ARCHITECTURE.md — OCR`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*
