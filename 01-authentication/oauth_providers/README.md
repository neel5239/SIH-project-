# External Auth Providers

**Module:** 01 — Authentication
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/01-authentication/oauth_providers`

---

## What this is for

The problem statement asks for authentication through established services. Delegating to Google or a similar provider means we never hold a password for those users, and staff onboarding becomes one click.

## What it does

- OAuth 2.0 / OIDC login through external identity providers
- Map the returned identity onto a MediKiosk user
- Link an external identity to an existing email or phone account
- Keep the provider list configurable — do not hardcode one

## What you build here

| File | Does |
|---|---|
| `base.py` | `AuthProvider` interface — every provider implements this |
| `google.py` | OIDC adapter |
| `callback.py` | handle the redirect, exchange the code, map the identity |
| `link.py` | link an external identity to an existing account |
| `config.py` | which providers are enabled, per deployment |

## Pipeline position

```
IN    provider redirect + authorisation code
OUT   a mapped user + a session
```

**Depends on:** provider credentials
**Feeds:** doctor portal (staff), patient app (optional)

## Definition of done

- [ ] **Provider abstraction from day one** — adding a second provider is a config change, not a rewrite
- [ ] State parameter validated on every callback — no CSRF
- [ ] An email returned by a provider is trusted only if the provider marks it verified
- [ ] Linking requires proving control of the existing account first

## Reference

- `docs/API_SPEC.md — Auth`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*
