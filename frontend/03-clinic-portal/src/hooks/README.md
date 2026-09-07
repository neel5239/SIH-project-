# hooks/ — live queue and desk logic

| File | Does |
|---|---|
| `useQueue.ts` | live clinic queue over `/ws/clinic/{id}` |
| `useSearch.ts` | debounced patient search |
| `useInvites.ts` | doctor invite status |
| `useAlertSound.ts` | **one chime per new red flag**, never duplicated on reconnect |

- [ ] The board updates with **no refresh** — an emergency surface that polls looks broken
- [ ] Queue state survives a dropped connection and replays what it missed
- [ ] Reconnecting must not re-fire alert sounds for flags already acknowledged
