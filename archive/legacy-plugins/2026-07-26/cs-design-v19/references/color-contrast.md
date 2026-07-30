# Color & Contrast Reference

## Contrast Requirements (WCAG AA)

| Content | Minimum Ratio |
|---|---|
| Normal text (<18px) | 4.5:1 |
| Large text (≥18px bold, ≥24px) | 3:1 |
| UI components, icons | 3:1 |
| Decorative elements | No requirement |

## Color Distribution: 60-30-10 Rule

- **60%**: Dominant neutral (background, surface)
- **30%**: Secondary (text, borders, secondary elements)
- **10%**: Accent (CTAs, highlights, interactive elements)

## Tinting Blacks and Whites

Never use pure `#000000` or `#ffffff`. Tint toward brand hue:

```css
/* Bad */
--color-text: #000000;
--color-bg: #ffffff;

/* Good */
--color-text: #0d0d14;  /* near-black with slight violet tint */
--color-bg: #fafaf8;    /* near-white with warm tint */
```

## Color Spaces

Use OKLCH for perceptually uniform palettes:
```css
--primary: oklch(60% 0.15 250);
--primary-light: oklch(80% 0.10 250);
--primary-dark: oklch(40% 0.20 250);
```

## Dark Mode

- Increase line-height by 0.05–0.1
- Reduce saturation slightly (vibrant colors look harsher on dark)
- Check ALL contrast ratios again (different from light mode)

## Semantic Token Naming

```css
--color-text-primary
--color-text-secondary
--color-surface-default
--color-surface-elevated
--color-action-primary
--color-action-danger
```
