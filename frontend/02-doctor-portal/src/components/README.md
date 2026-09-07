# components/ — where source attribution becomes touchable

| File | Does |
|---|---|
| `SourceTag.tsx` ★★ | `[Patient]` `[Rx 12/04/25]` `[Lab 05/08/26]` — tappable |
| `AudioReplay.tsx` ★★ | tap → **hear the patient's own words** |
| `ImageViewer.tsx` ★★ | tap → **see the actual ink** |
| `VerifyChip.tsx` | ⚠ unreadable · confidence 71% · confirm |
| `ConflictRow.tsx` | both sides, both sources, **never merged** |
| `SeverityPill.tsx` | ↑ ↓ 🚨 colour-coded, form not just text |
| `EditableLine.tsx` | a doctor edit → stored as a correction |
| `ConfirmBar.tsx` | **nothing is saved until this is pressed** |

## Non-negotiables

- [ ] **Audio starts in under 300 ms.** If it lags, the effect dies — cache resolved sources.
- [ ] A conflict is **two lines with two source tags**. Never one merged value.
- [ ] An unreadable item shows the **image**, never a confident guess.
- [ ] `ConfirmBar` is the only path into the patient's record.

> This is the most memorable ten seconds of the demo. Tap the line, let the audio play, and say
> nothing while it does.
