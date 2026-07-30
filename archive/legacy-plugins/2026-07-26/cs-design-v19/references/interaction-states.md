# Interaction States Reference

## The 8 Required Component States

Every interactive component MUST implement all 8:

```
1. default    — base state, no user interaction
2. hover      — mouse cursor over element
3. focus      — keyboard focus (:focus-visible)
4. active     — pressed / currently selected
5. disabled   — cannot interact (pointer-events: none)
6. loading    — async operation in progress
7. error      — validation failure or fetch error
8. success    — action completed successfully
```

## Focus Design Rules

```css
/* ✅ Good */
:focus-visible {
  outline: 2px solid var(--color-action-primary);
  outline-offset: 2px;
}

/* ❌ Bad — removes focus without replacement */
:focus { outline: none; }
```

Requirements:
- Minimum 3:1 contrast ratio for focus indicator
- 2–3px thickness
- Offset from element boundary
- Use `:focus-visible` (not `:focus`) to avoid showing on mouse click

## Form Patterns

```html
<!-- ✅ Good -->
<label for="email">Email address</label>
<input id="email" type="email" aria-describedby="email-error">
<span id="email-error" role="alert">Please enter a valid email</span>

<!-- ❌ Bad — placeholder only -->
<input type="email" placeholder="Email address">
```

Rules:
- ALWAYS use visible `<label>` (never placeholder-only)
- Error messages BELOW the field
- Use `aria-describedby` to associate errors
- Required fields: use `aria-required="true"` + visual indicator

## Loading Patterns

```jsx
// Inline spinner for button
<button disabled={loading}>
  {loading ? <Spinner size="sm" /> : null}
  {loading ? 'Saving...' : 'Save'}
</button>

// Skeleton for content loading
<Skeleton height={20} width="80%" />
```

## Destructive Actions: Undo > Confirm

```
❌ "Are you sure? [Cancel] [Delete]"  — friction, bad UX
✅ Delete happens immediately + "Undo" toast for 5s  — better UX
```

Exception: high-stakes irreversible actions (account deletion) → confirm dialog is OK.

## Overlay Positioning (Modern)

```css
/* CSS Anchor Positioning (Chrome 125+) */
.tooltip {
  position: absolute;
  anchor-name: --trigger;
  position-anchor: --trigger;
}

/* Fallback: Popover API */
<div popover>...</div>
```

Avoid `position: fixed` modals with manual `top/left` calculations.
