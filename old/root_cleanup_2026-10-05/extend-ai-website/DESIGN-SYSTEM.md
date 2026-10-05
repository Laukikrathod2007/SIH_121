# Extend.ai Design System
## Complete token reference for our drilling intelligence landing page

---

## 1. COLOR PALETTE

### Brand / Primary
```
Yellow (primary CTA, key highlights):
  --primary: #ffcc00          (pure brand yellow)
  --primary-muted: #ffb700    (slightly warmer yellow)

Orange scale (secondary accent, document processing):
  --orange-01: #eed7b3
  --orange-02: #f6dbb0
  --orange-03: #edb45a        ← active states, highlights
  --orange-04: #754c0b        ← dark orange text
```

### Backgrounds & Surfaces (Dark mode — our page)
```
--background:  #0a0a0a        ← page background (near-black)
--card:        #171717        ← card / panel surface
--muted:       #262626        ← slightly lifted surface
--accent:      #262626        ← same as muted (accent areas)

Surface scale (stone family):
  --color-stone-950: #0c0a09  ← deepest surface
  --color-stone-900: #1c1917  ← dark card
  --color-stone-800: #292524  ← raised panel
  --color-stone-700: #44403b  ← borders, dividers
  --color-stone-600: #57534d  ← secondary text bg
  --color-stone-500: #79716b  ← muted text
  --color-stone-400: #a6a09b  ← placeholder text
  --color-stone-300: #d6d3d1  ← light dividers
  --color-stone-200: #e7e5e4  ← light bg tint
  --color-stone-100: #f5f5f4  ← near-white bg
  --color-stone-50:  #fafaf9  ← white with warmth
```

### Text
```
--foreground (dark):    #fafafa   ← primary text on dark
--foreground (light):   #0a0a0a   ← primary text on light
--muted-foreground:     #a1a1a1   ← secondary text (dark mode)
--muted-foreground:     #737373   ← secondary text (light mode)
--elements-high-em:     #2a2823   ← high emphasis labels
--elements-mid-em:      #5b554a   ← medium emphasis
```

### Semantic / Status
```
Green (success, confirmed, relevant match):
  --green-01: #e0f6eb   (light bg)
  --green-02: #b0f6d3   (tint)
  --green-03: #129d58   ← active / confirmed
  --green-04: #097540   ← dark / hover

Blue (information, links, progress):
  --blue-01: #ddebfc    (light bg)
  --blue-02: #b0cff6    (tint)
  --blue-03: #1252a1    ← active blue
  --blue-04: #0a3a74    ← dark blue
  --color-blue-600: #155dfc   ← CTA blue
  --color-blue-700: #1447e6   ← deep CTA

Teal (live data, streaming):
  --teal-01: #e7f7f8
  --teal-02: #b1f3f6
  --teal-03: #14969d    ← live indicator
  --teal-04: #005b60    ← dark teal

Purple (AI / intelligence layer):
  --purple-01: #dbd8f6
  --purple-02: #b8b0f6
  --purple-03: #442ee8  ← AI actions
  --purple-04: #160a74  ← deep AI

Red (critical, errors, fault):
  --destructive: #e40014 / #ff6568
  --color-red-500: #fb2c36
  --color-red-600: #e40014
```

### Border / Overlay
```
--border (dark): #ffffff1a     ← 10% white (subtle border on dark)
--border-bubble: #8ba2c1       ← bubble / badge border
--input (dark):  #ffffff26     ← 15% white input border
```

---

## 2. TYPOGRAPHY

### Font Stack (7 custom fonts — all self-hosted woff2)

| Font | File | CSS Variable | Use case |
|---|---|---|---|
| **Systemia Variable** | `systemia-variable.woff2` | `--font-systemia` | Default body / `--font-sans` — all paragraphs |
| **ABC Favorit Regular** | `abc-favorit-regular.woff2` | `--font-abc-favorit` | Sub-headings, navigation labels |
| **ABC Favorit Bold** | `abc-favorit-bold.woff2` | `--font-abc-favorit` | Bold headings, CTAs |
| **Dwight Regular** | `dwight-regular.woff2` | `--font-dwight` | **Hero display type** — the large "Production-ready document processing" text |
| **Mindway** | `mindway.woff2` | `--font-mindway` | Stylised accent labels |
| **DM Mono Regular** | `dm-mono-regular.woff2` | `--font-mono` | Code blocks, technical values, badges |
| **Inter Variable** | `inter-variable.woff2` | `--font-inter` | Fallback / body alternative |

### Type Scale (complete)
```
Hero / Display:
  h1: 3.875rem / 3.875rem line-height / -1% tracking   (font: Dwight)
  h2: 3.5rem   / 3.5rem   / -.56px tracking
  h3: 3rem     / 3rem     / -.48px tracking
  h4: 2.75rem  / 2.75rem  / -1% tracking
  h5: 2.5rem   / 2.5rem   / -1% tracking
  h6: 2.25rem  / 2.25rem  / -.36px tracking
  h7: 1.75rem  / 2rem     / -.28px tracking
  h8: 1.5rem   / 1.75rem  / -.24px tracking

Body:
  xl:   1.25rem / 1.75rem / -2% tracking
  lg:   1.125rem / 1.625rem / -.36px tracking
  base: 1rem    / 1.5rem   / -.32px tracking
  sm:   0.875rem / 1.25rem / -2% tracking
  xs:   0.75rem  / 1.25rem / -2% tracking

Mono (DM Mono — for our telemetry / data values):
  mono-15: 0.9375rem / 6% letter-spacing
  mono-14: 0.875rem  / 6% letter-spacing
  mono-13: 0.8125rem / .78px letter-spacing
  mono-12: 0.75rem   / .72px letter-spacing
  mono-11: 0.6875rem / 1.1px letter-spacing
```

**Key observation:** Extend uses **tight negative tracking** on all display sizes and **positive tracking** on mono. This gives the clean engineering feel — tight headlines, airy data labels.

---

## 3. SPACING & LAYOUT

### Container widths
```
--spacing-desktop-container:    1152px   ← main content column
--spacing-desktop-container-xl: 1280px   ← wide sections
--spacing-tablet-container:      718px   ← tablet breakpoint
```

### Border radius
```
--radius:    0.625rem  (10px — main cards, buttons)
--radius-lg: 0.625rem
--radius-md: 0.5rem    (8px)
--radius-sm: 0.375rem  (6px)
--radius-xs: 0.25rem   (4px)   ← badges, tags
```

---

## 4. ANIMATION TOKENS

```
Default transition: 0.15s cubic-bezier(0.4, 0, 0.2, 1)
Ease-out:           cubic-bezier(0, 0, 0.2, 1)
Modal open:         0.25s cubic-bezier(0.22, 1, 0.36, 1)   ← spring feel
Modal close:        0.15s

Icon swap:
  duration:  0.2s
  ease:      ease-in-out
  start-scale: 0.25
  blur:      2px
```

---

## 5. SHADOWS

```
Soft elevation:     0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.1)
Medium elevation:   0 4px 6px rgba(0,0,0,0.1), 0 2px 4px rgba(0,0,0,0.1)
High elevation:     0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.1)
Glow (teal):        0 0 16px 6px rgba(45,160,212,0.45)   ← live indicator glow
Inner border:       inset 0 3px 0 var(--color-stone-300)
Dark inner:         0 0 0 1px rgba(28,25,23,0.18) inset
Highlight ring:     0 0 0 2px rgba(255,255,255,0.9)
```

---

## 6. COMPONENT PATTERNS

### Button — Primary (Yellow)
```css
background: #ffcc00;
color: #171717;
border-radius: var(--radius);           /* 10px */
font-family: var(--font-abc-favorit);
font-weight: 700;
letter-spacing: 0.06em;
text-transform: uppercase;
font-size: 0.875rem;
padding: 0.625rem 1.25rem;
transition: 0.15s ease-out;

hover: brightness(95%);
```

### Button — Secondary (Ghost / Outline)
```css
background: transparent;
border: 1px solid #ffffff1a;
color: #fafafa;
/* same font/size/padding as primary */
hover: background: #262626;
```

### Section counter badge  [01] / [02]
```css
font-family: var(--font-dm-mono);
font-size: 0.75rem;           /* mono-12 */
letter-spacing: 0.72px;
color: var(--muted-foreground);
text-transform: uppercase;
```

### Section label (above headline)  "TRUSTED BY LEADING AI TEAMS"
```css
font-family: var(--font-dm-mono);
font-size: 0.6875rem;         /* mono-11 */
letter-spacing: 1.1px;
color: var(--muted-foreground);
text-transform: uppercase;
```

### Card
```css
background: #171717;
border: 1px solid #ffffff1a;
border-radius: var(--radius);  /* 10px */
box-shadow: 0 1px 3px rgba(0,0,0,0.1);
```

### Code / SDK block (hero)
```css
background: #171717;
border: 1px solid #ffffff1a;
border-radius: var(--radius-sm);
font-family: var(--font-dm-mono);
font-size: 0.875rem;
color: #fafafa;
```

### Benchmark bar
```css
background: #262626;
accent-fill: #ffcc00;           /* Extend's own bar */
competitor-fill: #57534d;       /* competitor bars */
font: DM Mono, mono-12, uppercase tracking
```

---

## 7. LAYOUT PATTERNS (from page structure)

### Section numbering system  ( 01 / 04 )
- Top-right of each major section
- DM Mono, small, muted foreground
- Format: `( [current] / [total] )`

### Figure labels  FIG.06 / FIG.07
- Above feature screenshots
- DM Mono, mono-11 (0.6875rem)
- Letter-spacing: 1.1px
- Uppercase

### Feature pills  / parse  / extract  / split
- Left-border highlight (1px solid yellow or stone)
- DM Mono font
- Lowercase with slash prefix
- Active state: yellow border + yellow text

### Trusted logos strip
- Horizontal scroll on mobile
- Grayscale filter, opacity 0.6
- hover: opacity 1, grayscale removed
- 44px height, variable width

---

## 8. HOW TO APPLY THIS TO OUR PAGE

### Mapping extend.ai patterns → our drilling intelligence product

| Extend.ai element | Our equivalent |
|---|---|
| `( 01 / 04 )` section counter | `BEAT 01 / 13` scroll stage counter |
| `/ parse / extract / split` feature pills | `/ sense / predict / resolve` workflow pills |
| Hero code block `pip install extend-ai` | Hero telemetry block `ROP 33.6 m/hr  ECD 12.8 ppg` |
| Yellow CTA button | "Request Demo" / "Explore Platform" |
| Benchmark bars | Filter stages: 50 → 38 → 21 → 9 → 6 wells |
| FIG.06 label above screenshots | FIG.01 above wellbore hero, FIG.04 above fault diagram |
| Trusted logos strip | — (not needed, replace with stat strip) |
| Section label "TRUSTED BY LEADING AI TEAMS" | "INTELLIGENCE AT THE BIT" |
| Card with confidence score | Historical case result card |
| Processing mode toggle (speed/cost/accuracy) | Filter toggle (proximity/formation/fault-block) |

### Our page colour decisions (dark mode throughout)

```
Page background:     #0a0a0a        (--background)
Panel / card:        #171717        (--card)
Raised card:         #262626        (--muted)
Border:              rgba(255,255,255,0.10)  (--border dark)
Primary text:        #fafafa
Secondary text:      #a1a1a1
Caption / label:     #79716b

Current well dot:    #ffcc00        (brand yellow — THE focal point)
Relevant wells:      #edb45a        (orange-03 — secondary warm)
Fault line:          #fb2c36        (red-500 — danger/warning)
Irrelevant wells:    #44403b        (stone-700 — muted, ghost)
Formation layers:    rgba(255,204,0, 0.08) tinted overlays
Safe trajectory:     #00bb7f        (emerald-500 — green = safe)
Active trajectory:   #155dfc        (blue-600)
AI layer:            #442ee8        (purple-03)
Live/streaming:      #14969d        (teal-03)

Section counter:     DM Mono, #a1a1a1, 0.72px tracking
Hero headline:       Dwight, 3.875rem, -1% tracking, #fafafa
Sub-headline:        ABC Favorit Bold, 2.5rem, #fafafa
Body:                Systemia Variable, 1rem, #a1a1a1
Data / telemetry:    DM Mono, 0.875rem, 6% tracking, #ffcc00 or #fafafa
```

---

## 9. FONTS — @font-face declarations for our project

```css
/* Hero display — large headings */
@font-face {
  font-family: 'Dwight';
  src: url('/assets/fonts/dwight-regular.woff2') format('woff2');
  font-weight: 400;
  font-display: swap;
}

/* Primary sans — body, cards, nav */
@font-face {
  font-family: 'Systemia';
  src: url('/assets/fonts/systemia-variable.woff2') format('woff2');
  font-weight: 100 900;
  font-display: swap;
}

/* Sub-headings, CTAs */
@font-face {
  font-family: 'ABCFavorit';
  src: url('/assets/fonts/abc-favorit-regular.woff2') format('woff2');
  font-weight: 400;
  font-display: swap;
}
@font-face {
  font-family: 'ABCFavorit';
  src: url('/assets/fonts/abc-favorit-bold.woff2') format('woff2');
  font-weight: 700;
  font-display: swap;
}

/* Monospace — telemetry values, counters, badges, code */
@font-face {
  font-family: 'DMMonoExtend';
  src: url('/assets/fonts/dm-mono-regular.woff2') format('woff2');
  font-weight: 400;
  font-display: swap;
}

/* Accent / decorative labels */
@font-face {
  font-family: 'Mindway';
  src: url('/assets/fonts/mindway.woff2') format('woff2');
  font-weight: 400;
  font-display: swap;
}
```

---

## 10. WHAT MAKES EXTEND.AI FEEL PREMIUM

1. **Negative tracking on display text** — everything tighter than you expect, creates density
2. **Mono font for ALL technical values** — benchmarks, counters, section numbers, code
3. **Yellow as the ONLY colour on a near-black page** — every other colour is stone/neutral
4. **( 01 / 04 ) numbering** — visitor always knows where they are in the story
5. **FIG.XX labels** — makes it feel like an engineering document, not a marketing page
6. **`/ feature` pill labels** — slash prefix borrowed from file paths / CLI, feels technical
7. **10% white borders** — barely visible, creates depth without color
8. **No gradients** — flat surfaces, all depth comes from shade steps (stone-800 → stone-900)
9. **Uppercase mono labels** — every section opener is mono uppercase, body is mixed case
