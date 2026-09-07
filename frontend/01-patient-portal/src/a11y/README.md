# a11y/ — accessibility, a requirement not a stretch goal

The problem statement names this explicitly: audio-guided mode, large text, high contrast,
icon-driven, usable by a first-time non-tech-savvy patient.

| File | Does |
|---|---|
| `audioFirst.ts` | full navigation **without reading a word** |
| `contrast.ts` | large-text and high-contrast toggle, persistent for the session |
| `proxyMode.ts` | a relative is answering → tag those answers second-hand |
| `privacy.ts` | never render PII at full size — a queue is watching this screen |

- [ ] **A blindfolded tester can complete the questionnaire using audio only**
- [ ] Proxy-tagged answers reach the backend marked as second-hand — the doctor must know
- [ ] **Test standing up, at arm's length, in a bright room.** That is the real condition.
