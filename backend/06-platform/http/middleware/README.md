# Middleware

Applied to every request so six people are not each inventing conventions.

| File | Does |
|---|---|
| `auth.py` | verify the token, attach `user_id` and `role` to the request |
| `request_id.py` | generate and echo `X-Request-ID`, attach to every log line |
| `errors.py` | one error shape everywhere: `{ error: { code, message, request_id } }` |
| `ratelimit.py` | per user · per IP · per phone number |

- [ ] **PII redaction filter in the logger from day 1** — no name, phone, OTP or clinical text in a log
- [ ] A patient requesting another patient's data gets **403**, not an empty list
- [ ] Errors never leak a stack trace to the client
