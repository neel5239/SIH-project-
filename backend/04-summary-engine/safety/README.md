# Safety Check

**Module:** 04 — Summary Engine
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/04-summary-engine/safety`

---

## What this is for

The system must never diagnose and never recommend treatment. A prompt saying 'do not diagnose' is not a guarantee. A separate check is.

## What it does

- Inspect every generated line for diagnostic or treatment language
- Block and rewrite anything that crosses the line
- Log it and count it
- If the check itself is unavailable, **do not render the summary** — show the raw answers instead

## What you build here

| File | Does |
|---|---|
| `check.py` | the classifier |
| `labels.py` | diagnostic · therapeutic · clean, with examples |
| `rewrite.py` | reduce a violation to the underlying observation, or drop it |
| `counter.py` | the number we show: diagnostic statements emitted = 0 |

## Pipeline position

```
IN    every candidate summary line
OUT   pass, or block + rewrite + log
```

**Depends on:** a small classifier
**Feeds:** the doctor portal

## Definition of done

- [ ] *'findings suggest angina'* → **blocked** · *'should start metformin'* → **blocked** · *'patient reports chest pain for 3 days'* → passes
- [ ] **Fail closed.** Unavailable → raw answers with a banner. Never bypass.
- [ ] Counter is visible and reads zero
- [ ] Adversarial test: deliberately try to make it diagnose. It must not.

This is one of the strongest things we can show a judge: not a promise in a prompt, a number we measure.

## Reference

- `docs/ARCHITECTURE.md — safety`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*
