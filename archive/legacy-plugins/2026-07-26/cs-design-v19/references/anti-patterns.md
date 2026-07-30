# Design Anti-Patterns Reference

Based on impeccable's detection patterns. These are the most common "AI slop" indicators.

## Typography Anti-Patterns

| Anti-Pattern | Why Bad | Fix |
|---|---|---|
| Inter, Roboto, DM Sans as primary font | Overused default — signals AI/generic origin | Use a distinctive typeface matching brand voice |
| 8+ font sizes with <1.1× ratio | No clear hierarchy | 5-step scale with 1.25–1.5× ratio |
| Wider than 75ch body text | Reading fatigue | `max-width: 65ch` on paragraphs |
| Light text on dark bg at normal line-height | Reads too tight | Add 0.05–0.1 to line-height for light-on-dark |

## Color Anti-Patterns

| Anti-Pattern | Why Bad | Fix |
|---|---|---|
| Pure `#000000` or `#ffffff` | Harsh, clinical | Tint blacks/whites toward brand hue |
| Gray text on colored backgrounds | WCAG fail risk | Check 4.5:1 contrast ratio |
| Gradient text | Dated, accessibility issue | Solid color or subtle gradient bg instead |
| Monochromatic palette with no variation | Flat, no hierarchy | 60-30-10 distribution rule |

## Layout Anti-Patterns

| Anti-Pattern | Why Bad | Fix |
|---|---|---|
| Card-in-card (nested cards) | Visual noise, unclear hierarchy | Flatten; use spacing/borders instead |
| Side-stripe borders (3px+ left/right) | Signature AI tell | Use background fill or top border |
| Spacing not on 4pt grid | Visual inconsistency | 4px base unit: 4, 8, 12, 16, 24, 32, 48, 64px |
| Fixed px spacing (non-scalable) | Breaks on different screens | Use rem-based spacing tokens |

## Interaction Anti-Patterns

| Anti-Pattern | Why Bad | Fix |
|---|---|---|
| `outline: none` without replacement | Keyboard inaccessible | Custom `:focus-visible` style instead |
| Placeholder-only labels | Disappears on input | Add visible `<label>` elements |
| Error message above field | Hard to associate | Error below field with `aria-describedby` |
| No loading state | User confusion | Add loading indicator on async actions |
| No disabled state | Confusing UX | Style disabled elements distinctly |
| Confirmation dialogs for destructive actions | Friction | Undo pattern is better UX |

## Component State Anti-Patterns

Every interactive component MUST have these 8 states:
1. `default` — base appearance
2. `hover` — mouse over
3. `focus` — keyboard focus (via `:focus-visible`)
4. `active` — pressed/selected
5. `disabled` — not interactive
6. `loading` — async in progress
7. `error` — validation or fetch failed
8. `success` — action confirmed

Missing any of these is an anti-pattern.
