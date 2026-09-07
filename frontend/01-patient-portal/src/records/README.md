# records/ — the patient's own medical record

For most of these patients this is the **first time they have ever held their own medical record
in a readable form.** That is a real outcome and worth a line in the pitch.

| File | Shows |
|---|---|
| `MyVisits.tsx` | every visit, across every clinic they attended |
| `VisitDetail.tsx` | summary + prescription + the documents we digitised |
| `LabTrends.tsx` | values plotted over time — "your HbA1c is coming down" |
| `AudioRecap.tsx` | the summary read aloud **in their own language** |

- [ ] Only their **own** records — enforced server-side, not just hidden in the UI
- [ ] **Never show a raw clinical code without its plain-language label**
- [ ] The audio recap is a first-class control, not a hidden extra
- [ ] Assume a low-end Android phone on a bad connection
