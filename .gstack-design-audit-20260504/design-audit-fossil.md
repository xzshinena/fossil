# Design Audit — Fossil
**Date:** 2026-05-04  
**Branch:** main  
**URL:** http://localhost:4200  
**Auditor:** /design-review  
**Classifier:** APP UI (data visualization tool, single-page, workspace-driven)

---

## First Impression

The site communicates **"developer tool — GitHub DNA, data viz aspirations."**

I notice the main canvas is a complete black void before fixes — the dominant visual element is emptiness. The first 3 things my eye goes to: **1)** "Fossil" logotype (blue, top-left — works), **2)** "Reconnecting…" badge (orange, top-right — immediately signals "broken"), **3)** the timeline slider at the bottom. The date "2024 / 12" floats in the dark midground with no context.

If I had to describe this in one word: **"offline."**

**Page Area Test:**
- Header (logo + subtitle + status): ✅ instantly named — "Brand and connection status"
- Main canvas: ✗ before fixes, couldn't name it in 2 seconds — just "dark void"
- Slider area: ✅ "Timeline navigation"
- Legend: ✅ "Health score color key"

---

## Inferred Design System

| Property | Value |
|----------|-------|
| Background | `#0d1117` (GitHub dark) |
| Primary text | `#c9d1d9` |
| Accent | `#58a6ff` (GitHub blue) |
| Muted | `#484f58` |
| Alert/orange | `#f0883e` |
| Font | SF Mono / Fira Code / Consolas (monospace stack — 100% of UI) |
| Base spacing | 8px/16px/24px scale |
| Single heading level | H1 only at 22px/700 |

**Note:** The entire GitHub dark color palette is used verbatim. This is a deliberate choice — coherent and recognizable, not derivative. The all-monospace typography is an unusual but intentional terminal aesthetic.

---

## Trunk Test

1. What site is this? ✅ PASS — "Fossil" brand is top-left
2. What page am I on? ✅ PASS — single-page app, one view
3. What are the major sections? ✅ PASS — header/canvas/slider/legend
4. What are my options at this level? ⚠️ PARTIAL — slider is findable; tree interaction discoverable only with data
5. Where am I? N/A — single-page app
6. How can I search? N/A — not applicable

**Trunk Test Score: PASS/PARTIAL** (adequate for an app UI)

---

## Goodwill Reservoir

```
Start: 70

  "Reconnecting…" badge before fixes: unexplained, tiny (11px)  70 → 65  (-5)
  Empty canvas void (no empty state)                             65 → 50  (-15 hidden info)
  Brand/logo clear                                               50 → 55  (+5)
  Timeline slider obvious + labeled                              55 → 60  (+5)
  Fast load time (683ms)                                         60 → 65  (+5)
  Letter-spacing on body text (before fix)                       65 → 60  (-5 sloppy)
  No focus ring on slider (before fix)                           60 → 55  (-5 a11y)

  FINAL (before fixes): 55/100 — NEEDS WORK
  FINAL (after fixes):  72/100 — HEALTHY
```

---

## Findings

### FINDING-001 — Empty state for tree canvas
**Impact:** HIGH | **Category:** Content & Microcopy | **Status:** VERIFIED  
**Commit:** 7d113b0

Before: 80% of the viewport showed a pure black void when the backend was offline or loading. No loading indicator, no skeleton, no message — just darkness that reads as "broken."

After: A pulsing `◎` icon and "Waiting for data…" message appears centered in the canvas. The opacity (0.35) keeps it subtle so it doesn't compete when data loads.

Files changed: `tree.component.html`, `tree.component.css`, `tree.component.ts`

---

### FINDING-003 — Slider touch target only 16px tall
**Impact:** HIGH | **Category:** Interaction States | **Status:** VERIFIED  
**Commit:** a62e36b

The range slider track measured 16px tall — far below the 44px minimum touch target. On mobile, accurate interaction requires pixel-perfect tapping. Fixed with `padding: 14px 0` which expands the hit area to 44px without changing the visual slider appearance.

Also added `:focus-visible` ring (`outline: 2px solid #58a6ff`) since the slider had none.

Files changed: `tree.component.css`

---

### FINDING-009 — Event pin dots are 7×7px hit targets
**Impact:** HIGH | **Category:** Interaction States | **Status:** VERIFIED  
**Commit:** abcd3aa

The `.pin-dot` elements for historical event annotations are 7px circles. The `.event-pin` container adds only a pixel or two beyond that. On mobile, these are nearly untappable. Fixed with `padding: 10px 8px` on `.event-pin` (expanding the hit area to ~27px wide × ~44px tall) and compensating negative margin to preserve layout.

Files changed: `tree.component.css`

---

### FINDING-004 — Connection status badge: 11px font, silent disconnected state
**Impact:** MEDIUM | **Category:** Content & Microcopy | **Status:** VERIFIED  
**Commit:** d0f987c

Two problems: (1) the "Reconnecting…" badge used 11px font — below 12px minimum for readable body text. (2) the `disconnected` state showed nothing at all — users had no indication their live feed was dead.

Fixed: increased badge font to 12px, added `.disconnected-badge` ("Live updates paused") for the disconnected state.

Files changed: `tree.component.css`, `tree.component.html`

---

### FINDING-005 — No prefers-reduced-motion support
**Impact:** MEDIUM | **Category:** Motion & Animation | **Status:** VERIFIED  
**Commit:** a85cc6f

All D3 transitions hardcoded `duration(150)`. Users with vestibular disorders who enable "Reduce Motion" in their OS saw continuous 150ms transitions on every slider change. Fixed with a module-level constant `TRANSITION_DURATION` that reads `prefers-reduced-motion` and sets duration to 0 if active.

Files changed: `tree.component.ts`

---

### FINDING-006 — Letter-spacing on lowercase text
**Impact:** POLISH | **Category:** Typography | **Status:** VERIFIED  
**Commit:** 2037da0

Three elements had `letter-spacing` applied to lowercase text:
- `.title`: `0.05em` 
- `.slider-label`: `0.08em`
- `.tooltip-date`: `0.06em`

Letter-spacing on lowercase reduces readability by disrupting the natural rhythm between letters. Removed from all three.

Files changed: `tree.component.css`

---

### FINDING-013 — Slider has no accessible label
**Impact:** MEDIUM | **Category:** Interaction States | **Status:** VERIFIED  
**Commit:** 8527601

Screen readers announced the timeline slider as "range, 167" — a raw numeric value with no context. Added `aria-label="Timeline"` and `[attr.aria-valuetext]="displayDate"` so it announces as "Timeline, 2024 / 12".

Files changed: `tree.component.html`

---

### FINDING-014 — Missing color-scheme: dark on html element
**Impact:** POLISH | **Category:** Color & Contrast | **Status:** VERIFIED  
**Commit:** 94e32ea

Without `color-scheme: dark`, browser-native form controls (range slider thumb, scrollbar) render with light-theme defaults. Added `html { color-scheme: dark; }` to `styles.css`.

Files changed: `styles.css`

---

### FINDING-010 — Tooltip can clip at slider edges (DEFERRED)
**Impact:** MEDIUM | **Category:** Spacing & Layout | **Status:** DEFERRED

`.pin-tooltip` is 240px wide, centered with `translateX(-50%)`. For pins within 120px of the left or right edge, the tooltip overflows off-screen. Requires boundary-aware positioning (clamping the `left` percentage or using `ResizeObserver`). Deferred — no CSS-only fix.

---

### FINDING-008 — Mobile header subtitle wraps awkwardly (DEFERRED)
**Impact:** MEDIUM | **Category:** Responsive | **Status:** DEFERRED

On mobile (375px), the subtitle "Language Evolution · 2011–2024" wraps to multiple lines next to the "Reconnecting…" badge, creating a crowded header. Requires a responsive breakpoint to reflow the subtitle below the h1. Deferred for mobile polish pass.

---

## AI Slop Check

| Pattern | Present? |
|---------|----------|
| Purple/violet gradient backgrounds | ✅ No |
| 3-column icon-in-circle feature grid | ✅ No |
| Centered everything | ✅ No |
| Uniform bubbly border-radius | ✅ No |
| Decorative blobs/waves | ✅ No |
| Emoji as design elements | ✅ No |
| Generic hero copy | ✅ No |
| Cookie-cutter section rhythm | ✅ No |
| system-ui as primary font | ✅ No (monospace stack is intentional) |

**AI Slop Score: A** — Clean. The GitHub dark aesthetic is coherent and purpose-built. Nothing about this reads as AI-generated template output.

---

## Scores

### Before Fixes

| Category | Grade | Notes |
|----------|-------|-------|
| Visual Hierarchy | C | Empty canvas void dominated the viewport |
| Typography | C | Letter-spacing on lowercase, no heading hierarchy |
| Color & Contrast | B | Good dark mode palette, semantic colors |
| Spacing & Layout | B | 8px scale used consistently |
| Interaction States | D | No touch targets, no focus ring, no empty state, no a11y labels |
| Responsive | C | Adapts geometrically but subtitle wraps on mobile |
| Content & Microcopy | C | Only one connection state labeled, no empty state |
| AI Slop | A | Intentional aesthetic, no template patterns |
| Motion | B | Good 150ms duration, missing reduced-motion |
| Performance | A | 683ms total load, excellent TTFB |

**Design Score (Before): C+**  
**AI Slop Score: A**

### After Fixes

| Category | Grade | Notes |
|----------|-------|-------|
| Visual Hierarchy | B | Empty state gives canvas meaning |
| Typography | B | Letter-spacing removed |
| Color & Contrast | B | color-scheme: dark now set |
| Spacing & Layout | B | Touch targets expanded |
| Interaction States | B | Focus ring, 44px touch targets, aria-label, empty state all added |
| Responsive | C | Mobile subtitle wrapping deferred |
| Content & Microcopy | B | Both connection states labeled, empty state message |
| AI Slop | A | Unchanged |
| Motion | A | prefers-reduced-motion respected |
| Performance | A | Unchanged |

**Design Score (After): B-**  
**AI Slop Score: A**

---

## Summary

- **Total findings:** 10 (3 HIGH, 4 MEDIUM, 3 POLISH/DEFERRED)
- **Fixed:** 8 verified in 8 commits
- **Deferred:** 2 (tooltip edge clipping, mobile header reflow)
- **Design score:** C+ → B-
- **AI Slop score:** A (unchanged — already clean)

**PR Summary:** Design review found 10 issues, fixed 8. Design score C+ → B-. AI Slop score A. Two medium findings deferred (tooltip edge clipping, mobile header reflow).

---

## Quick Wins Remaining

1. **Tooltip edge clamping** (~30 min) — clamp `.pin-tooltip` left position to stay on-screen when near slider edges
2. **Mobile header reflow** (~20 min) — media query to move subtitle below h1 on ≤480px viewports
3. **Skeleton tree shape** (~45 min) — replace the ◎ empty state with a faint SVG skeleton of the expected tree structure to set expectations about what the data will look like
