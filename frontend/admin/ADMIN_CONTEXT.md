# ADMIN — the ops and evidence surface

**User:** hospital ops, the team, and — for eight minutes — the judges
**Driven by:** M6 metrics endpoints · M5 Guardian log

---

## This is a demo asset, not just an ops tool

Minute 7:15 of the pitch is this screen.

---

## Components

| Component | Endpoint | Shows |
|---|---|---|
| `GuardianCounter.jsx` | `/admin/metrics/guardian` | `outputs 14,203 · blocked 61 · **diagnostic emitted 0**` |
| `AccuracyChart.jsx` | `/admin/metrics/accuracy` | field accuracy by section and source module, over time |
| `LatencyPanel.jsx` | `/admin/metrics/latency` | turn p50 / p95, per-stage breakdown, **engine mix** |
| `OfflineState.jsx` | `/health/deps` | online / offline, outbox depth, dead-letter count |

---

## The two lines to say out loud

**On the Guardian counter:**
> "'Never diagnoses' is not a promise in our prompt. It is a number we measure."

**On the engine mix, after pulling the network cable:**
> "Bhashini when we have a network, local models when we don't. Patient audio never left the building."

---

## Design notes

- Big numbers. This is read from a few metres away during a demo.
- `emitted_diagnostic` gets its own tile and should read **0**.
- Show the trend, not just the current value — a system that visibly improves beats a static one.
- Dead-lettered jobs surface here. **Never silently discarded.**
