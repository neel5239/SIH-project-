# components/ — input primitives that work without literacy

These are what accessibility actually means in this product.

| File | Why it exists |
|---|---|
| `MicButton.tsx` | large, with a live level meter, so the patient can see it heard them |
| `OptionCard.tsx` | icon + label, thumb-sized — the icon must work **without** the label |
| `ProgressDots.tsx` | **mandatory** — patients need to see the end coming |
| `SpeakAgain.tsx` | replay the current prompt, any number of times |
| `SkipButton.tsx` | **always visible** — nothing is mandatory |
| `BigButton.tsx` | 64 px minimum touch target, everywhere |

- [ ] Every icon is recognisable by someone who cannot read a single word
- [ ] Touch targets at least 64 px
- [ ] Everything works at the large-text setting
- [ ] Focus is visible for keyboard and switch access
