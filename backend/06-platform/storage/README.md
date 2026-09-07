# File Storage

**Module:** 06 — Platform
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/06-platform/storage`

---

## What this is for

Audio recordings, uploaded documents, crops and generated audio. All of it sensitive.

## What it does

- Store and serve blobs
- Keep the **original** of every document forever within the retention policy
- Delete raw audio after transcription unless the patient consented to keep it
- Serve pre-cut audio clips so replay on the doctor's screen is instant

## What you build here

| File | Does |
|---|---|
| `store.py` | put / get / delete |
| `audio.py` | recordings + clip cutting |
| `documents.py` | originals + crops |
| `retention.py` | what is deleted when |
| `signed_urls.py` | time-limited access |

## Pipeline position

```
IN    files from the patient app
OUT   stored blobs + time-limited URLs
```

**Depends on:** object storage
**Feeds:** modules 02, 03, 05

## Definition of done

- [ ] The original document image is never overwritten
- [ ] Raw audio is deleted after transcription **unless the patient consented** to keep it
- [ ] Audio clips are pre-cut server-side so playback starts in under 300 ms
- [ ] No blob is publicly reachable — every URL is signed and time-limited

## Reference

- `docs/ARCHITECTURE.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*
