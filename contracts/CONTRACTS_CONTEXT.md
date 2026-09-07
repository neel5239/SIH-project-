# CONTRACTS — shared data models

**Owner:** Member 6 (M6) · **Imported by:** everyone
**Deep spec:** [`docs/DATA_CONTRACTS.md`](../docs/DATA_CONTRACTS.md)

---

## Why this folder exists

These are the objects that cross module boundaries. They are the interface between six people
working in parallel. If they drift, the project breaks in the last 12 hours — which is exactly
when you cannot afford it.

**This folder is the single source of truth.** `docs/DATA_CONTRACTS.md` documents it; this code
enforces it.

---

## Files

| File | Object | Produced by | Consumed by |
|---|---|---|---|
| `session.py` | `Session` | M1 | everyone |
| `consent.py` | `Consent` | M1 | M2, M5, M6 |
| `slot.py` | `Slot`, `SlotSource` | M3 | M5 |
| `doc_entity.py` | `DocEntity`, payload variants | M4 | M5 |
| `provenance.py` | `Provenance` | M3, M4, physician | M5 enforces, M6 serves |
| `alert.py` | `Alert` | M3, M4, M5 | M6 |
| `summary.py` | `ClinicalSummary`, `Correction` | M5 | M1, M6, frontend |
| `enums.py` | languages, sections, severities, states | — | everyone |
| `version.py` | `CONTRACT_VERSION` | M6 | contract tests |

---

## Rules

1. **Pydantic v2.** Typed, validated, no bare dicts crossing a boundary.
2. **Never import a module's internals to get a shape.** Import from here.
3. **Changing anything here** requires: a message to the whole team, a `CONTRACT_VERSION` bump,
   an update to `docs/DATA_CONTRACTS.md`, and updated mock fixtures.
4. `tests/test_contracts.py` runs in CI. A violation fails the build.

---

## Deliverable — day 1

All nine files, complete, importable. This unblocks five people.
