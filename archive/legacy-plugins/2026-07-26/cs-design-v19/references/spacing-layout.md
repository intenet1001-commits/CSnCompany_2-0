# Spacing & Layout Reference

## 4pt Grid System

All spacing values MUST be multiples of 4px:

```
4px   (0.25rem)  — tight: icon padding, small gaps
8px   (0.5rem)   — compact: button padding-y, inline gaps
12px  (0.75rem)  — small: form field gaps
16px  (1rem)     — base: default spacing unit
24px  (1.5rem)   — medium: section padding, card gaps
32px  (2rem)     — large: section margins
48px  (3rem)     — xl: page section spacing
64px  (4rem)     — 2xl: major page divisions
96px  (6rem)     — 3xl: hero sections
```

## Semantic Spacing Tokens

```css
--space-xs: 0.25rem;
--space-sm: 0.5rem;
--space-md: 1rem;
--space-lg: 1.5rem;
--space-xl: 2rem;
--space-2xl: 3rem;
--space-3xl: 4rem;
```

## Visual Hierarchy via Spacing

White space = primacy. More space around an element = higher importance.

**Squint Test**: Blur your vision. You should still see:
1. Primary content (largest, most space)
2. Secondary content (medium)
3. Grouped elements (tighter spacing within groups)

## Grid Systems

- **12-column grid**: for complex layouts (dashboards, marketing pages)
- **4-column grid**: for mobile
- **CSS Grid**: preferred over Flexbox for 2D layouts
- **Container queries**: use for component-level responsive behavior

## Common Layout Patterns

```css
/* Content container */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-lg);
}

/* Card grid */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-lg);
}
```
