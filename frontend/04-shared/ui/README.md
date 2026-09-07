# UI — two themes, one system

**The patient screen and the doctor screen must not look alike.**

```
PATIENT THEME  (patient.css)        CLINICAL THEME  (clinical.css)
huge type, huge buttons             dense, structured
high contrast                       four fixed sections
almost no typing                    source tag on every line
audio before text                   tabular numerals
icons on every option               editable in place
64 px touch targets                 fast to scan, not to read
```

| File | Does |
|---|---|
| `tokens.css` | colour · type scale · spacing · severity colours |
| `patient.css` | the patient theme |
| `clinical.css` | the doctor theme |
| `AudioPlayer.jsx` | used by both — patient recap and doctor source replay |

- [ ] **Never mix the two themes**
- [ ] Severity colour is never reused as a brand accent
- [ ] Devanagari and Tamil need more line-height than Latin — check it
- [ ] Everything works at the large-text setting
