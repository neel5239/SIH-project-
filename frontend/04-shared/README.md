# Shared Frontend

**Module:** Frontend — shared
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `frontend/shared`

---

## What this is for

One copy of what both apps need — but **two different design languages** inside it. The patient screen and the doctor screen must not look alike.

## What it does

- Typed API client for both apps
- WebSocket layer for the doctor portal
- Two themes: PATIENT (huge, spoken, icons) and CLINICAL (dense, structured)
- UI strings for the patient app

## What you build here

| File | Does |
|---|---|
| `api/client.js` | base fetch: auth, request id, errors |
| `api/auth.js` |  |
| `api/questionnaire.js` |  |
| `api/documents.js` |  |
| `api/doctor.js` |  |
| `ws/socket.js` | doctor push channel |
| `ui/patient.css` | ★ huge type, huge buttons, high contrast |
| `ui/clinical.css` | ★ dense, structured, tabular numerals |
| `ui/tokens.css` | colour · type scale · spacing · severity |
| `ui/AudioPlayer.jsx` | used by both apps |
| `i18n/index.js` | UI chrome strings |
| `i18n/strings/` | one file per language — UI chrome ONLY |

## Pipeline position

```
IN    —
OUT   shared client + themes
```

**Depends on:** backend contracts
**Feeds:** both apps

## Definition of done

- [ ] **Never PII in a URL** — enforce it in the client
- [ ] The two themes never mix
- [ ] **Clinical text never comes from `i18n`.** Questions and summaries come from the backend at runtime.
- [ ] Keep this folder small — a component only one app uses belongs in that app

## Reference

- `docs/ARCHITECTURE.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*
