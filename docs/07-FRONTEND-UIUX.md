# 07 — Frontend / UI-UX Specification

> **STATUS: PLACEHOLDER — awaiting design detail from the team lead.**
>
> The structural decisions are already made and are documented in the per-surface CONTEXT files.
> This document will hold the visual and interaction specification once the dashboards are designed.

---

## What is already decided (do not re-litigate)

**Five surfaces, not one responsive app.** Five genuinely different users.

| Surface | User | Context file |
|---|---|---|
| `frontend/kiosk/` | Patient at the kiosk | [KIOSK_CONTEXT.md](../frontend/kiosk/KIOSK_CONTEXT.md) |
| `frontend/doctor-console/` | Physician, 20 seconds | [DOCTOR_CONSOLE_CONTEXT.md](../frontend/doctor-console/DOCTOR_CONSOLE_CONTEXT.md) |
| `frontend/triage-board/` | Triage nurse | [TRIAGE_BOARD_CONTEXT.md](../frontend/triage-board/TRIAGE_BOARD_CONTEXT.md) |
| `frontend/patient-dashboard/` | Patient, later, on a phone | [PATIENT_DASHBOARD_CONTEXT.md](../frontend/patient-dashboard/PATIENT_DASHBOARD_CONTEXT.md) |
| `frontend/admin/` | Ops and judges | [ADMIN_CONTEXT.md](../frontend/admin/ADMIN_CONTEXT.md) |

**Kiosk rules** — one question per screen · spoken before read · voice OR tap on every question ·
nothing mandatory except consent · patient can stop at any point.

**Doctor console** — a scanning surface, not a document viewer. Four panels. Alerts before detail.
Severity encoded in form, not only text. Tap a line to hear the patient; tap a box to see the ink.

**Triage board** — WebSocket push, never polling. Red flags pinned with the rule that fired.

---

## Still to be specified — fill this in

- [ ] Visual language: palette, type scale, spacing, iconography
- [ ] Kiosk screen-by-screen wireframes (9 screens)
- [ ] Icon set for every closed-question option (must be recognisable without text)
- [ ] Body diagram artwork and hit regions
- [ ] Face scale artwork (6 faces)
- [ ] Doctor console panel layout and responsive behaviour
- [ ] Triage board large-format layout (readable across a room)
- [ ] Patient dashboard mobile-first layout
- [ ] Motion: what animates, what does not (red-flag state especially)
- [ ] Empty, loading, and error states for every surface
- [ ] Accessibility audit checklist: contrast, focus order, screen-reader labels, touch targets
- [ ] Localisation: how a 22-language UI handles text expansion and Indic line breaking

---

## When you write this section

Bring: how each dashboard should look, and how each user moves through it.
Everything structural above is already fixed and should be treated as constraints, not suggestions.
