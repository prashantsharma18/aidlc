# Accessibility Checklist

A quick reference for WCAG 2.1 AA compliance. Use it together with the `building-user-interfaces` skill.

## Table of Contents

- [Essential Checks](#essential-checks)
- [Common HTML Patterns](#common-html-patterns)
- [Testing Tools](#testing-tools)
- [Quick Reference: ARIA Live Regions](#quick-reference-aria-live-regions)
- [Common Anti-Patterns](#common-anti-patterns)

## Essential Checks

### Keyboard Navigation
- [ ] Every interactive element can be focused with the Tab key
- [ ] Focus order matches the visual and logical order
- [ ] Focus is visible (an outline or ring on focused elements)
- [ ] Custom widgets support the keyboard (Enter to activate, Escape to close)
- [ ] No keyboard traps (the user can always Tab away from a component)
- [ ] Skip-to-content link at top of page - visible (at least) on keyboard focus
- [ ] Modals keep focus inside while open and return focus on close

### Screen Readers
- [ ] Every image has `alt` text (or `alt=""` for decorative images)
- [ ] Every form input has an associated label (`<label>` or `aria-label`)
- [ ] Buttons and links have descriptive text, not "Click here"
- [ ] Icon-only buttons have `aria-label`
- [ ] Page has one `<h1>` and headings don't skip levels
- [ ] Changes to dynamic content are announced (`aria-live` regions)
- [ ] Tables have `<th>` headers with scope

### Visual
- [ ] Text contrast ≥ 4.5:1 (normal text) or ≥ 3:1 (large text, 18px+)
- [ ] UI components contrast ≥ 3:1 against background
- [ ] Color is not the only way to convey information
- [ ] Text can be resized to 200% without breaking the layout
- [ ] Nothing flashes more than 3 times per second

### Forms
- [ ] Every input has a visible label
- [ ] Required fields are marked (not by color alone)
- [ ] Error messages are specific and tied to the field
- [ ] The error state shows more than color (icon, text, border)
- [ ] Form submission errors are summarized and can take focus
- [ ] Known fields use autocomplete (for example, `type="email" autocomplete="email"`)

### Content
- [ ] The language is declared (`<html lang="en">`)
- [ ] Page has a descriptive `<title>`
- [ ] Links stand out from surrounding text (not by color alone)
- [ ] Touch targets ≥ 44x44px on mobile
- [ ] Empty states carry meaning (no blank screens)

## Common HTML Patterns

### Buttons vs. Links

```html
<!-- Use <button> for actions -->
<button onClick={handleDelete}>Delete Task</button>

<!-- Use <a> for navigation -->
<a href="/tasks/123">View Task</a>

<!-- NEVER use div/span as buttons -->
<div onClick={handleDelete}>Delete</div>  <!-- BAD -->
```

### Form Labels

```html
<!-- Explicit label association -->
<label htmlFor="email">Email address</label>
<input id="email" type="email" required />

<!-- Implicit wrapping -->
<label>
  Email address
  <input type="email" required />
</label>

<!-- Hidden label (visible label preferred) -->
<input type="search" aria-label="Search tasks" />
```

### ARIA Roles

```html
<!-- Navigation -->
<nav aria-label="Main navigation">...</nav>
<nav aria-label="Footer links">...</nav>

<!-- Status messages -->
<div role="status" aria-live="polite">Task saved</div>

<!-- Alert messages -->
<div role="alert">Error: Title is required</div>

<!-- Modal dialogs -->
<dialog aria-modal="true" aria-labelledby="dialog-title">
  <h2 id="dialog-title">Confirm Delete</h2>
  ...
</dialog>

<!-- Loading states -->
<div aria-busy="true" aria-label="Loading tasks">
  <Spinner />
</div>
```

### Accessible Lists

```html
<ul role="list" aria-label="Tasks">
  <li>
    <input type="checkbox" id="task-1" aria-label="Complete: Buy groceries" />
    <label htmlFor="task-1">Buy groceries</label>
  </li>
</ul>
```

## Testing Tools

```bash
# Automated audit
# Accessibility checkers (axe-core, pa11y or equivalent): the repository's pinned tools named in
# AGENTS.md; never install one to run this.

# In browser
# Chrome DevTools → Lighthouse → Accessibility
# Chrome DevTools → Elements → Accessibility tree

# Screen reader testing
# macOS: VoiceOver (Cmd + F5)
# Windows: NVDA (free) or JAWS
# Linux: Orca
```

## Quick Reference: ARIA Live Regions

| Value | Behavior | Use For |
|-------|----------|---------|
| `aria-live="polite"` | Announced at the next pause | Status updates, saved confirmations |
| `aria-live="assertive"` | Announced immediately | Errors, time-sensitive alerts |
| `role="status"` | Works like `polite` | Status messages |
| `role="alert"` | Works like `assertive` | Error messages |

## Common Anti-Patterns

| Anti-Pattern | Problem | Fix |
|---|---|---|
| `div` as button | Not focusable, and no keyboard support | Use `<button>` |
| Missing `alt` text | Screen readers cannot see the images | Add descriptive `alt` |
| Color-only states | Color-blind users cannot see them | Add icons, text, or patterns |
| Autoplaying media | Disorienting, and it can't be stopped | Add controls, don't autoplay |
| Custom dropdown with no ARIA | Keyboard and screen reader users cannot use it | Use native `<select>` or proper ARIA listbox |
| Removing focus outlines | Users can't see where focus is | Style outlines, don't remove them |
| Empty links/buttons | "Link" is announced with no description | Add text or `aria-label` |
| `tabindex > 0` | Breaks the natural tab order | Use `tabindex="0"` or `-1` only |
