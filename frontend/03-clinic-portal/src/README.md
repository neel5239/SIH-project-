# src/ — clinic portal

```
src/
├── api/          its OWN backend calls
├── pages/        Register · Dashboard · Doctors ★ · Reception ★ · QueueBoard · Settings
├── components/   search · quick-register · assign · token · queue row · red-flag alert
└── hooks/        queue · search · invites · alert sound
```

**Two users, one app.** `routes.tsx` sends `CLINIC_ADMIN` to `Dashboard` and `RECEPTIONIST`
to `Reception`.

Reference: `frontend/03-clinic-portal/README.md`
