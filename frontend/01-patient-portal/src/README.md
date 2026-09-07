# src/ — patient portal

```
src/
├── api/            its OWN backend calls
├── auth/           ① login — phone + OTP is the primary path
├── questionnaire/  ② SPEAK or TYPE, on every question
│   ├── speak/          SUB-MODULE A
│   └── type/           SUB-MODULE B
├── documents/      ③ opens only if the patient said yes to reports
├── records/        my visits · lab trends · audio recap
├── components/     the input primitives that work without literacy
├── hooks/          intake · capture QC · idle · offline
└── a11y/           audio-first · contrast · proxy · privacy
```

Reference: `frontend/01-patient-portal/README.md`
