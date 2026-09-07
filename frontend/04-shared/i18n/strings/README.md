# UI Strings

One file per language. **UI chrome only** — buttons, labels, screen titles, error text.

> **Clinical content never lives here.** Questions and summaries come from the backend at runtime.

- [ ] `en.json` is the key source of truth; every other file mirrors its keys
- [ ] A missing key falls back to English, never to a blank
- [ ] **Start with Hindi + English + one regional language, perfected.** Not twenty on day one.
- [ ] Test the longest translation for layout breaks — Hindi and Tamil run visibly longer
