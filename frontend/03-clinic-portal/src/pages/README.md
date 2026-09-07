# pages/ — two users, one app

`routes.tsx` sends `CLINIC_ADMIN` to `Dashboard` and `RECEPTIONIST` to `Reception`.

| File | Role | Does |
|---|---|---|
| `Register.tsx` | — | ★ clinic self-registration + the first admin account |
| `Login.tsx` | — | staff login |
| `Dashboard.tsx` | ADMIN | today: patients · average wait · intake completion · red flags |
| `Doctors.tsx` | ADMIN | ★★ **add a doctor by name + email** → invite → status tracked |
| `Reception.tsx` | RECEPTION | ★★ search / quick-register / **assign to a doctor** / token |
| `QueueBoard.tsx` | both | live queue, red flags pinned, no refresh |
| `Settings.tsx` | ADMIN | departments · OPD hours · languages offered |

## The two screens that matter

**`Doctors.tsx`** is the step that binds every doctor's dashboard to this clinic. The doctor
never types a clinic name — the signed invite carries it.

**`Reception.tsx`** is what gives every intake a destination. Without an assignment, a completed
questionnaire has nowhere to go.

- [ ] **A receptionist sees no clinical content.** Identity, doctor, department, token.
- [ ] Quick-register takes under 20 seconds of typing
- [ ] Assignment suggests doctors by department **and** by a language the patient speaks
