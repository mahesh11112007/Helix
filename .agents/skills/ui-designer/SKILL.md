---
name: UI Designer
description: Design modern, visually stunning, and highly engaging user interfaces with rich aesthetics following the Kiraak Design System.
---

# UI Designer — Kiraak Design System

## Mission
Design every page as a premium AI SaaS application with a clean, modern, and highly polished interface comparable to ChatGPT, Linear, Notion, Raycast, and Obsidian.

---

## Design Tokens

### Spacing (8px System)
```
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
--space-16: 64px;
```

### Border Radius
```
--radius-sm: 8px;
--radius-md: 12px;
--radius-lg: 16px;
--radius-xl: 20px;
--radius-full: 9999px;
```

### Shadows (Subtle Elevation)
```
--shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.05);
--shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.06);
--shadow-md: 0 4px 6px rgba(0, 0, 0, 0.07), 0 2px 4px rgba(0, 0, 0, 0.06);
--shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.08), 0 4px 6px rgba(0, 0, 0, 0.05);
--shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.1), 0 8px 10px rgba(0, 0, 0, 0.06);
```

### Animation Timing
```
--ease-out: cubic-bezier(0.16, 1, 0.3, 1);
--ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
--duration-fast: 150ms;
--duration-normal: 200ms;
--duration-slow: 300ms;
```

---

## Typography

- **Font Family**: `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`
- Load Inter from Google Fonts: `https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap`

### Scale
| Token        | Size   | Weight | Use Case            |
|-------------|--------|--------|---------------------|
| `display`   | 36px   | 700    | Hero / landing      |
| `h1`        | 28px   | 700    | Page titles         |
| `h2`        | 22px   | 600    | Section headers     |
| `h3`        | 18px   | 600    | Card titles         |
| `body`      | 15px   | 400    | Body text           |
| `body-sm`   | 13px   | 400    | Secondary text      |
| `caption`   | 12px   | 500    | Labels, metadata    |

### Line Heights
- Headings: `1.2–1.3`
- Body: `1.5–1.7`

---

## Color System

### Dark Mode (Default)
```
--bg-primary: #0F1117;
--bg-secondary: #161922;
--bg-tertiary: #1C1F2E;
--bg-elevated: #232738;
--border-primary: rgba(255, 255, 255, 0.08);
--border-secondary: rgba(255, 255, 255, 0.04);
--text-primary: #F1F3F5;
--text-secondary: #8B92A5;
--text-tertiary: #5C6370;
```

### Light Mode
```
--bg-primary: #FFFFFF;
--bg-secondary: #F8F9FB;
--bg-tertiary: #F0F2F5;
--bg-elevated: #FFFFFF;
--border-primary: rgba(0, 0, 0, 0.08);
--border-secondary: rgba(0, 0, 0, 0.04);
--text-primary: #1A1D27;
--text-secondary: #6B7280;
--text-tertiary: #9CA3AF;
```

### Accent Color
```
--accent: #6366F1;           /* Indigo-500 — primary CTA */
--accent-hover: #818CF8;     /* Lighter on hover */
--accent-muted: rgba(99, 102, 241, 0.12); /* Subtle backgrounds */
```

### Semantic Colors
```
--success: #22C55E;
--warning: #F59E0B;
--error: #EF4444;
--info: #3B82F6;
```

---

## Component Guidelines

### Sidebar
- Width: `260px` (collapsible to `64px`).
- Background: `--bg-secondary`.
- Active item: accent background with `--accent-muted`, bold text.
- Icons: 20px, using Lucide or Heroicons.
- Smooth collapse animation (`--duration-normal`).

### Top Navigation
- Sticky, `position: sticky; top: 0`.
- Height: `56–64px`.
- Contains breadcrumbs, search, and user avatar.
- Blurred background: `backdrop-filter: blur(12px)`.

### Cards
- Background: `--bg-elevated`.
- Border: `1px solid var(--border-primary)`.
- Border-radius: `--radius-lg` (16px).
- Padding: `--space-6` (24px).
- Shadow: `--shadow-sm`.
- Hover: elevate to `--shadow-md` with `transform: translateY(-1px)`.

### Buttons
| Variant    | Background          | Text            | Border              |
|-----------|---------------------|-----------------|---------------------|
| Primary   | `--accent`          | White           | None                |
| Secondary | `--bg-tertiary`     | `--text-primary`| `--border-primary`  |
| Ghost     | Transparent         | `--text-secondary`| None              |
| Danger    | `--error`           | White           | None                |

- Height: `36–40px`.
- Border-radius: `--radius-md` (12px).
- Transition: `all var(--duration-fast) var(--ease-out)`.

### Forms
- Input height: `40–44px`.
- Border: `1px solid var(--border-primary)`.
- Focus: `2px solid var(--accent)` ring.
- Label: `caption` size, `--text-secondary`.
- Error messages in `--error` color, 13px.

### Tables
- Clean, borderless rows.
- Row hover: `--bg-tertiary`.
- Header: `caption` style, uppercase, `--text-tertiary`.
- Alternating row colors optional (prefer hover highlight).

### Search Bar
- Rounded pill shape (`--radius-full`).
- Placeholder: "Search..." with `⌘K` shortcut hint.
- Background: `--bg-tertiary`.

### Loading States
- **Skeleton**: Pulsing `--bg-tertiary` blocks with rounded corners matching the content shape.
- **Spinner**: Small, indigo-colored SVG spinner (20px).
- **Progress Bar**: Thin, smooth-filling bar with accent color.

### Empty States
- Centered illustration or icon.
- Title + description + CTA button.
- Muted colors, inviting tone.

### Error States
- Red-tinted card with `--error` accent.
- Clear error message + retry action.
- No raw error codes shown to users.

---

## Dashboard Layout

```
┌──────────────────────────────────────────────┐
│ Sidebar │  Top Nav (sticky, blurred)         │
│         │────────────────────────────────────│
│ Logo    │  KPI Cards (3–4 in a row)          │
│ Nav     │────────────────────────────────────│
│ Items   │  Charts (2-col grid)               │
│         │────────────────────────────────────│
│ Bottom  │  Recent Activity │ Quick Actions   │
│ Actions │  AI Suggestions  │                 │
└──────────────────────────────────────────────┘
```

- Use CSS Grid: `grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))`.
- KPI cards: icon + metric + trend indicator.
- Charts: use Chart.js or Recharts, themed to match palette.

---

## Responsive Breakpoints

| Token  | Width    | Use Case         |
|--------|----------|------------------|
| `sm`   | 640px    | Mobile landscape |
| `md`   | 768px    | Tablet           |
| `lg`   | 1024px   | Small desktop    |
| `xl`   | 1280px   | Desktop          |
| `2xl`  | 1536px   | Large desktop    |

- Sidebar collapses to a hamburger menu below `lg`.
- Grid columns reduce from 4 → 2 → 1.

---

## Prohibitions

1. **No Bootstrap aesthetics** — no default blue buttons, card-body patterns, or generic utility grids.
2. **No excessive glassmorphism** — use it only for the top navbar blur, nowhere else.
3. **No heavy gradients** — solid, flat colors with subtle hover shifts.
4. **No inconsistent spacing** — always use the 8px spacing tokens.
5. **No mixed design languages** — one cohesive system everywhere.
6. **No cluttered interfaces** — generous whitespace, progressive disclosure.

---

## Quality Checklist

Before shipping any UI, verify:

- [ ] Uses Inter font loaded from Google Fonts.
- [ ] All spacing uses 8px multiples.
- [ ] Border-radius is 12–16px on cards and containers.
- [ ] Shadows are subtle (no harsh black drop-shadows).
- [ ] Animations are 150–250ms with easing curves.
- [ ] Dark mode is the default, light mode is supported.
- [ ] Accent color is used sparingly (CTAs, active states).
- [ ] Empty, loading, and error states are designed.
- [ ] Layout is responsive from 320px to 1536px+.
- [ ] Looks comparable to ChatGPT, Linear, or Notion in quality.
