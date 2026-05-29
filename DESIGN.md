---
name: clippr
description: Local-first AI video tool that converts any recording into vertical short-form clips with speaker tracking and burned-in captions.
colors:
  darkroom-black: "#0f0f13"
  panel-charcoal: "#1e1e1e"
  input-well: "#2a2a2a"
  terminal-void: "#09090b"
  primary-ink: "#e8e8e8"
  dim-ink: "#888888"
  iris: "#6c63ff"
  status-success: "#10b981"
  status-warning: "#f59e0b"
  status-error: "#ef4444"
typography:
  headline:
    fontFamily: "Geist, system-ui, -apple-system, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.3px"
  title:
    fontFamily: "Geist, system-ui, -apple-system, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "normal"
  body:
    fontFamily: "Geist, system-ui, -apple-system, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "Geist, Inter, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.02em"
  caption:
    fontFamily: "Geist, system-ui, -apple-system, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "normal"
  micro:
    fontFamily: "Geist, system-ui, -apple-system, sans-serif"
    fontSize: "11px"
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: "0.02em"
  mono:
    fontFamily: "Geist Mono, 'Fira Code', ui-monospace, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
rounded:
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "10px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-default:
    backgroundColor: "rgba(255,255,255,0.08)"
    textColor: "{colors.primary-ink}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
    typography: "{typography.label}"
  button-default-hover:
    backgroundColor: "rgba(255,255,255,0.13)"
    textColor: "{colors.primary-ink}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
  button-primary:
    backgroundColor: "{colors.iris}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "10px 22px"
    typography: "{typography.label}"
  button-primary-hover:
    backgroundColor: "#8078ff"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "10px 22px"
  button-icon:
    backgroundColor: "rgba(255,255,255,0.06)"
    textColor: "rgba(255,255,255,0.85)"
    rounded: "{rounded.sm}"
    padding: "6px 8px"
  button-icon-hover:
    backgroundColor: "rgba(255,255,255,0.1)"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "6px 8px"
  button-selected:
    backgroundColor: "rgba(108,99,255,0.22)"
    textColor: "#c4b5fd"
    rounded: "{rounded.md}"
    padding: "10px 16px"
  card:
    backgroundColor: "{colors.panel-charcoal}"
    rounded: "{rounded.lg}"
    padding: "16px 18px"
  input-field:
    backgroundColor: "{colors.input-well}"
    textColor: "{colors.primary-ink}"
    rounded: "{rounded.sm}"
    padding: "8px 12px"
  input-field-focus:
    backgroundColor: "{colors.input-well}"
    textColor: "{colors.primary-ink}"
    rounded: "{rounded.sm}"
    padding: "8px 12px"
---

# Design System: clippr

## 1. Overview

**Creative North Star: "The Dark Room"**

clippr is a professional instrument, not a consumer app. The visual system takes its cue from the controlled, deliberate environments where precision work gets done: the film darkroom, the mixing booth, the machine room. Everything runs in low ambient light. The interface is quiet so the content — the video, the speakers, the output clips — is always the loudest thing on the screen. Decoration is prohibited not for aesthetic reasons but for functional ones: this is a tool people use repeatedly, often under time pressure, and visual noise costs them.

The palette descends from near-black through tonal charcoals, using depth to separate function rather than color. One accent — Iris Violet — marks where the machine is active: selections, focus states, running processes. It appears infrequently, which makes it informative. The type scale is tight and deliberate; fonts are system-tuned sans-serifs that carry precision without calling attention to themselves.

This system explicitly rejects the warm-neutral SaaS aesthetic (cream backgrounds, sand surfaces, `--paper` tokens), the cluttered panel-maximalism of professional video editors, and the performative vocabulary of AI marketing tools (gradient orbs, glowing hero sections, "seamless" language). None of those belong in a dark room.

**Key Characteristics:**
- Near-black foundation with tonal charcoal layers — no warm tint, no blue shift
- Single violet accent used exclusively for active states and primary actions
- Restrained type scale: system sans at calibrated weights, mono for terminal output
- Shadows are state-driven, not structural — surfaces are flat at rest
- Motion is brief and functional: feedback and transitions, no choreography
- Density is a feature — tight spacing carries authority, not cramped-ness

## 2. Colors: The Darkroom Palette

Five neutral depth tiers plus one active accent plus three semantic status colors. The neutrals carry the full visual weight of the interface; the accent is reserved for interactive signal.

### Primary
- **Iris Violet** (`#6c63ff`): The single brand accent. Used for: the primary CTA (Generate button), checked/active toggle states, input focus rings, selected states, the spinner and cursor blink in the log stream. Any element that is currently selected, actionable, or in-progress uses Iris. Nothing else does.

### Neutral
- **Darkroom Black** (`#0f0f13`): The application body background. Near-black with a faint violet undertone — not warm, not cool gray. Nothing darker is needed.
- **Panel Charcoal** (`#1e1e1e`): Card and panel surfaces. The primary container background. Sits above the body.
- **Input Well** (`#2a2a2a`): Input fields, toggle group backgrounds, secondary surfaces within panels. Third elevation tier.
- **Terminal Void** (`#09090b`): Log stream background. The deepest surface, reserved for the terminal/mono context. Its near-absolute darkness signals machine output.
- **Primary Ink** (`#e8e8e8`): All primary text on dark surfaces. Warm near-white — not pure `#ffffff`, which would read as harsh. Contrast against Darkroom Black: 14:1.
- **Dim Ink** (`#888888`): Secondary text, labels, helper copy, placeholder text. Contrast against Panel Charcoal: 4.6:1 — meets WCAG AA body-text threshold. Do not go dimmer.

### Semantic Status
- **Emerald Run** (`#10b981`): Processing complete, success state. Progress bar fill on done.
- **Amber Hold** (`#f59e0b`): Warning, stalled state, soft errors.
- **Signal Red** (`#ef4444`): Error state. Progress bar, error log lines, destructive confirmations.

### Named Rules
**The One Signal Rule.** Iris Violet (`#6c63ff`) is the only non-status color used for interactive signal. It does not appear on decorative elements, headings, or icons at rest. The moment something glows violet, the user knows: this is active, selected, or running. Its rarity is the point.

**The Depth-As-Structure Rule.** The five neutral tiers map directly to elevation: Darkroom Black (body) → Panel Charcoal (cards) → Input Well (inputs/toggles) → Terminal Void (log stream). Never reverse this order — a darker surface inside a lighter one breaks the spatial model.

## 3. Typography

**Primary Font:** Geist Sans (Google), with `system-ui, -apple-system, 'Segoe UI', sans-serif` fallback stack.
**Mono Font:** Geist Mono (Google), with `'Fira Code', ui-monospace, monospace` fallback.

**Character:** A matched pair from the same type family. Geist Sans carries all UI text; Geist Mono is exclusively for the log stream and any machine-output text. The two weights contrast cleanly: regular body, medium labels, semibold headings. No display font, no serif.

### Hierarchy
- **Headline** (700, 18px, lh 1.2, ls −0.3px): Application-level identifiers only. The app name "clippr" in the header. One per screen.
- **Title** (600, 15px, lh 1.3): Section headings, card titles, panel names. "Speakers", "Settings", "Output".
- **Body** (400, 14px, lh 1.5): Input field values, file names, primary descriptive text. The workhorse size.
- **Label** (500, 13px, lh 1.4, ls 0.02em): Button text, interactive labels, speaker names in rows. Medium weight signals interactivity.
- **Caption** (400, 12px, lh 1.4): Metadata, stats, secondary sub-text. File duration, frame counts, language selections.
- **Micro** (500, 11px, lh 1.3, ls 0.02em): Field labels above inputs, format tags, footer hints. The smallest readable size at this scale.
- **Mono** (400, 12px, lh 1.6): Log stream lines, machine output only. Never used in UI labels.

### Named Rules
**The Mono Quarantine Rule.** Geist Mono appears only in the log stream and any direct terminal/machine output surfaces. It is not for code snippets in copy, not for numeric values in stats, not for IDs. Mono font signals: this came from the machine, not the interface.

**The Weight-Is-Role Rule.** 400 = content. 500 = interactive. 600–700 = headings. Do not use bold weight on body text for emphasis; use a different size or a dedicated label if emphasis is needed.

## 4. Elevation

clippr uses tonal layering, not shadows, as its primary depth vocabulary. The five neutral tiers (Darkroom Black → Panel Charcoal → Input Well → Terminal Void) define the elevation stack. A surface's background color communicates where it sits in the Z-axis.

Shadows exist, but only as state responses — not as structural decoration on resting elements.

### Shadow Vocabulary
- **Accent Glow** (`0 2px 12px rgba(108,99,255,0.35)`): Applied to the primary CTA (Generate button) at rest. The only ambient shadow in the system — it signals "this button is available." Intensifies to `0 2px 24px rgba(108,99,255,0.6)` during active processing (pulse-glow animation).
- **Iris Selection Glow** (`0 2px 8px rgba(108,99,255,0.25)`): Applied to selected/toggled buttons. Low-intensity, indicates active state.
- **Button Lift** (`0 4px 8px rgba(0,0,0,0.35)` + `0 2px 4px rgba(0,0,0,0.25)`): Applied to default glass buttons on hover. Conveys physical press response. Only on hover, not at rest.

### Named Rules
**The Flat-at-Rest Rule.** Cards, panels, and containers have no box-shadow at their default state. Depth is communicated by background color alone. Shadows appear only in response to state: hover, selection, or active processing. If a component has a shadow and it is not hoverable, selected, or actively processing, the shadow is decorative and should be removed.

## 5. Components

### Buttons

The direction for buttons is precise and minimal. The current implementation uses frosted glass (backdrop-filter) and layered shadows; these are acceptable as current state but should simplify over time toward thin-border, flat surfaces that respond to interaction rather than decorating resting states.

- **Shape:** Gently rounded (8px radius, `{rounded.md}`). 6px (`{rounded.sm}`) for icon-only variants.
- **Default:** Thin semi-transparent surface (`rgba(255,255,255,0.08)` background, `1px solid rgba(255,255,255,0.15)` border), Primary Ink text. Used for secondary actions (language toggle, mode switches, change file).
- **Hover/Focus (Default):** Background lifts to `rgba(255,255,255,0.13)`. `translateY(-1px)` lift. `outline: 2px solid rgba(108,99,255,0.6)` on `:focus-visible`.
- **Primary (CTA):** Iris Violet (`#6c63ff`) filled, white text, Accent Glow shadow. Used once per screen for the primary action (Generate). On hover: lightens to `#8078ff`.
- **Selected (Toggle):** Iris-tinted surface (`rgba(108,99,255,0.22)` background, Iris border), violet-200 text (`#c4b5fd`). Used for toggle groups (clip count, framing mode).
- **Icon:** Minimal surface (`rgba(255,255,255,0.06)` background, 6px radius, 6×8px padding). For compact row-level actions.
- **Disabled:** `opacity: 0.4`, `cursor: not-allowed`, no pointer-events, no lift.
- **Loading:** The primary button enters `pulse-glow` animation during active processing — Accent Glow oscillates between 35% and 60% opacity over 1.8s.

### Cards / Containers

- **Corner Style:** Gently rounded (10px, `{rounded.lg}`)
- **Background:** Panel Charcoal (`#1e1e1e`)
- **Border:** 1px `rgba(255,255,255,0.08)` — barely visible. Defines the container against the body without adding visual weight.
- **Elevation Strategy:** No box-shadow. Background color is the only depth signal.
- **Internal Padding:** 16px top/bottom, 18px left/right (`card-body`). Panel headers use the same horizontal padding with 14px vertical.

### Inputs / Fields

- **Style:** Input Well background (`#2a2a2a`), 1px `rgba(255,255,255,0.12)` border, 6px radius.
- **Text:** Primary Ink (14px, weight 600 for number inputs; 13px weight 400 for select dropdowns).
- **Focus:** Border shifts to Iris Violet (`#6c63ff`). No glow, no shadow — the border color change is the entire signal.
- **Placeholder / Dim labels:** Dim Ink (`#888`) for field labels (micro, 11px). Must remain at or above 4.5:1 against Input Well background.
- **Select Dropdowns:** SVG chevron background (`rgba(136,136,136,1)` stroke); option backgrounds use Panel Charcoal (`#1e1e1e`) to avoid platform-default white backgrounds breaking the dark context.
- **Toggle Groups:** Input Well container (`#2a2a2a` background, 1px `rgba(255,255,255,0.12)` border, 8px radius). Active segment: Iris Violet fill, white text. Inactive: Dim Ink text.

### Progress Bar

A thin (6px / `h-1.5`) horizontal fill bar on a Zinc-800 (`#27272a`) track. Three fill states:
- **Running:** Iris-to-blue gradient (`from-purple-600 to-blue-500`), `animate-pulse` while active.
- **Done:** Emerald Run (`#10b981`) solid fill.
- **Error:** Signal Red (`#ef4444`) solid fill.

### Log Stream (Signature Component)

The log stream is the most distinctive component in the system. Terminal Void background (`#09090b`), Geist Mono 12px, 1.6 line height, Zinc-800 border, 12px radius. Log lines display a line number prefix in Zinc-600 (visually dim, non-selectable), followed by the log text in Zinc-400. The cursor blink (a purple `▌` in `animate-pulse` at Iris Violet) indicates running state. Error lines are Signal Red. This component should never use a sans font; Mono Quarantine Rule applies.

### Speakers Row

Each speaker row uses the full card width: checkbox (16px, Iris Violet checked background), avatar circle (22px, `rgba(255,255,255,0.08)` background), editable name input, stats in Dim Ink, transcript preview in Dim Ink italic. Row separator: `rgba(255,255,255,0.06)` 1px border. Hover: `rgba(255,255,255,0.02)` background tint. No side-stripe borders.

## 6. Do's and Don'ts

### Do:
- **Do** use Iris Violet (`#6c63ff`) exclusively for interactive signal: focus rings, checked states, active selections, running process indicators. Let its rarity make it meaningful.
- **Do** maintain the tonal depth stack: Darkroom Black (body) → Panel Charcoal (cards) → Input Well (inputs). Shallower surfaces are lighter; going deeper means going darker.
- **Do** keep Dim Ink (`#888`) as the floor for all secondary text on dark surfaces. Anything dimmer than `#888` on `#1e1e1e` risks falling below 4.5:1 WCAG AA contrast.
- **Do** use Geist Mono exclusively for machine output (log stream). All UI text — labels, buttons, headings, captions — uses Geist Sans.
- **Do** show progress concretely: stage name, percentage, and the live log stream. The machine is working; the user should see it working.
- **Do** pair every status color with a text label or icon — never rely on color alone to communicate error, warning, or success states.
- **Do** apply `focus-visible` outlines (2px Iris Violet offset-2) to every interactive element. The dark surfaces make focus rings easy to skip; they are required.
- **Do** use `@media (prefers-reduced-motion: reduce)` alternatives for the pulse-glow animation and any entrance transitions.

### Don't:
- **Don't** use warm-neutral backgrounds. No cream, sand, beige, paper, linen, or any near-white with a warm tint (OKLCH C > 0.03, hue 40–100). The body is Darkroom Black.
- **Don't** introduce a second accent color. There is one: Iris Violet. The legacy blue CTA (`#2563eb`) is deprecated — migrate primary action buttons to Iris.
- **Don't** build Adobe/Premiere-style interfaces: no persistent multi-panel layouts, no sprawling toolbars, no floating palettes. Complexity lives in a single progressive-disclosure settings section.
- **Don't** use gradient text (`background-clip: text` + gradient). Emphasis is weight or size.
- **Don't** use side-stripe borders (`border-left` greater than 1px) as a card or callout accent. Full-border containers or background tints only.
- **Don't** animate layout properties (width, height, top, left) for progress. The progress bar fill animates `width` via `transition: all 500ms` — this is acceptable because it is a single, intentional data-bound value, not a decorative layout shift.
- **Don't** put shadows on resting panels or cards. The Flat-at-Rest Rule: shadows exist as hover or active state responses only.
- **Don't** use uppercase tracked text (`letter-spacing > 0.04em` + `text-transform: uppercase`) on more than 2–3 elements per screen. Field labels use `letter-spacing: 0.02em` without all-caps; that is the maximum.
- **Don't** use glassmorphism decoratively. The current `backdrop-filter: blur(8px)` on buttons is acceptable as a subtle layer effect; blurred panels behind content, or glass-card aesthetics for decoration, are prohibited.
- **Don't** display "Nothing here" as an empty state. Empty states should tell the user what to do: the upload zone is the correct pattern — a clear instruction and a visible affordance.
