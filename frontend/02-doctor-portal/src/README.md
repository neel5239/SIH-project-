# src/ — doctor portal

```
src/
├── api/          its OWN backend calls
├── pages/        Login · AcceptInvite · PatientList · PatientView
├── sections/     ★★ the four fixed sections
├── components/   SourceTag · AudioReplay · ImageViewer · VerifyChip · ConfirmBar
└── hooks/        queue · patient view · source · edit
```

**Section order is fixed:** ① info → ② summary → ③ questionnaire → ④ reports.

Reference: `frontend/02-doctor-portal/README.md`
