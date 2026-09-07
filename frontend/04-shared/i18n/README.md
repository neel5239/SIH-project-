# Localisation

UI chrome in the patient's language. **Clinical content is localised by the backend at runtime.**

| File | Does |
|---|---|
| `index.js` | provider + hook |
| `strings/` | one file per language — UI chrome only |
| `expansion.js` | layout guards for long translations |

- [ ] **Clinical text never comes from here.** Questions and summaries come from the backend.
- [ ] Switching language mid-questionnaire loses nothing
- [ ] **Hindi + English + one regional language, perfected.** Not twenty on day one.
