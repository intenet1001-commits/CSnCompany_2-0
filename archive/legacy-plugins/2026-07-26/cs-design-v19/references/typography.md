# Typography Reference

## Type Scale

Use a **5-step modular scale** with 1.25–1.5× ratio between steps.

```
xs:  0.75rem  (12px)
sm:  0.875rem (14px)
base: 1rem    (16px)
lg:  1.25rem  (20px)
xl:  1.5rem   (24px)
2xl: 2rem     (32px)
3xl: 2.5rem   (40px)
```

**Marketing/content pages**: fluid sizing with `clamp()` for headings.
**App UIs/dashboards**: fixed `rem` scales (no fluid type).

## Line Height

- Body text: 1.5–1.6
- Headings: 1.1–1.2
- Light text on dark: add 0.05–0.1 extra
- Narrow columns: tighter leading; wide columns: more spacing

## Line Length

- Body text: `max-width: 65ch` (75ch max)
- UI labels: no restriction

## Font Pairing

Select fonts based on brand voice words (NOT "modern" or "elegant").
Write 3 concrete brand words first, then choose fonts.

**Fonts to avoid** (overused defaults):
- Inter, Roboto, DM Sans, System-ui
- Fraunces, Newsreader, Lora, Playfair Display (overused "editorial")
- IBM Plex family (overused "technical")

## Semantic Token Naming

```css
/* Good */
--text-body: 1rem;
--text-heading-lg: 2rem;

/* Bad */
--font-size-16: 1rem;
--font-size-32: 2rem;
```
