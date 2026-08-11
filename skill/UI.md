---
name: minimal-pyqt-desktop-app-ui
description: "Use when designing or building the visual style for a Python desktop application UI with PyQt6 or PySide6 and you want a simple, clean, modern, native-feeling design system: quiet neutral surfaces, one restrained accent color, comfortable consumer-app density, and disciplined typography — light mode by default. Covers QSS tokens, layout structure (sidebar, toolbar, content, cards), hover/focus states, and what to avoid."
---

# Minimal PyQt Desktop App UI Skill

## Use When
- Designing or building the UI for a Python desktop app with **PyQt6** or **PySide6**.
- The brief asks for "simple", "clean", "minimal", "modern", "friendly" desktop software — not a marketing site, not a mobile app, not a dense pro/technical tool.
- Starting a new app shell (window, sidebar, toolbar, content) and you need a full design system, not a single widget.
- This skill defaults to **light mode only** and **comfortable/consumer density**. If a project needs dark mode or a compact/pro density instead, see "Tuning knobs" below — the token structure supports both, only the values change.

## Scope
- Covers: window structure, sidebar, toolbar, content surfaces, cards, buttons, inputs, lists, scrollbars, menus, typography, color, spacing, motion.
- Does not cover: packaging/distribution (PyInstaller, briefcase, etc.), app icons, or multi-window/dialog architecture beyond basic styling.
- Ships as a design-token file (`scripts/theme.py`) plus a runnable reference (`demo/demo_app.py`) — copy patterns from the demo into your own app, don't import the demo file directly.

## Core principle
**Design furniture, not decoration.** A desktop app is used for long stretches at a time. Every surface should read as calm and structural by default — hierarchy comes from spacing and font weight, not shadows and gradients. Spend visual boldness on exactly one accent color and nothing else.

## Visual target
- Neutral surfaces first: window background → panel background (sidebar/toolbar) → content background, separated by a 1px hairline border (`QFrame` with `border: 1px solid`), not a drop shadow.
- One accent color, used only for the primary button, selection state, and the active nav item. Never let a second saturated color compete with it.
- Consistent corner radius: 6px for small controls (inputs, list rows), 10px for cards/panels. Avoid 16px+ "app icon" radii — they read as mobile, not desktop.
- Flat by default. Reserve elevation (a subtle border + slightly heavier background, since Qt's native drop-shadow support is limited) for things that float above content: `QMenu`, popovers, dialogs. Sidebar and toolbar never get a shadow.
- Native OS title bar by default (simplest, always looks correct). Only build a custom frameless title bar (`Qt.FramelessWindowHint`) if the brief specifically asks for full brand control over the window chrome — see "Tuning knobs".

## Typography
- Use the OS system font, not a bundled webfont — `get_system_font()` in `scripts/theme.py` picks `.AppleSystemUIFont` / `"Segoe UI"` / `"Ubuntu"` per platform via `platform.system()`. Qt's `QFont` doesn't support CSS-style fallback lists, so pick explicitly rather than relying on QSS `font-family` alone.
- Base body size **14px** (comfortable/consumer). A compact/pro variant would use 13px — see "Tuning knobs".
- Type scale: 11px (caption/meta) → 14px (body) → 15px (section label) → 22px (view title, used once per screen, never a giant hero headline).
- Weight carries hierarchy: regular body, medium (500) for labels/nav/buttons, semibold (600) for section labels and view titles. Avoid bold walls of text.
- Set via `QLabel.setProperty("role", "title" | "section" | "caption" | "secondary")` and the matching QSS selectors in `theme.py` — don't set font size/weight inline per-widget.
- **Card titles must match across mechanisms.** A panel that mixes hand-built card headers (a `role="section"` `QLabel` + optional badge in a `QHBoxLayout`) with native `QGroupBox` titles needs both to resolve to the exact same size/weight (`font_size_section`, 600). Style `QGroupBox::title` explicitly to that spec — don't rely on the OS-native default, which can silently differ by a pixel or two and read as an inconsistent design system even though each card is individually "correct."

## Color (light mode tokens)
| Token | Value | Use |
|---|---|---|
| `window_bg` | `#F5F5F7` | outermost window background |
| `panel_bg` | `#FAFAFA` | sidebar, toolbar |
| `content_bg` | `#FFFFFF` | cards, inputs, list rows |
| `border` | `#E5E5EA` | hairline between surfaces |
| `text_primary` | `#1D1D1F` | body text, labels |
| `text_secondary` | `#6E6E73` | captions, meta, placeholders |
| `accent` | `#0A84FF` | primary button, selection, active nav |
| `accent_hover` / `accent_pressed` | derived | button/nav interaction states |
| `accent_soft` | `rgba(10,132,255,0.12)` | selection background, active-nav background |

- The accent is a sensible default (Apple system blue). If the project already has a brand color, swap `THEME.accent` — every hover/pressed/selection state derives from it automatically, don't hand-pick new hex values for each state.
- Selection and active-nav backgrounds use `accent_soft` (10–15% opacity), not a filled block — reserve the filled block for the one primary button.
- This skill is scoped to light mode only per the current brief. If dark mode is added later, duplicate `Theme` as `DARK_THEME` with the same field names and swap the surfaces/text per the dark-mode base below — keep every token name identical so widget code never has to change:
  `window #1E1E1E → panel #252526/#2B2B2D → border #3A3A3C → text #F5F5F7 / #98989D`.

## Implementation guidance (PyQt6 / PySide6 specifics)
- **Tokens live in one file.** `scripts/theme.py` defines a frozen `Theme` dataclass (`THEME`) and `build_stylesheet(theme) -> str`. Apply once: `app.setStyleSheet(build_stylesheet(THEME))`. Never hardcode a hex color or pixel radius inside a widget file — read it from `THEME.<token>` for anything QSS doesn't cover (e.g. `setFixedWidth(THEME.sidebar_width)`).
- **QSS has no variables.** Unlike CSS, Qt stylesheets can't reference custom properties, so the token file builds the final QSS string with an f-string. If you add a new token, add it to `Theme` and reference it in `build_stylesheet`, not as a magic number in a `.setStyleSheet()` call somewhere else.
- **State variants via dynamic properties, not subclassing.** Use `widget.setProperty("variant", "primary")` / `setProperty("nav", "true")` / `setProperty("card", "true")` and match them in QSS with `QPushButton[variant="primary"]`. This keeps one `QPushButton` class usable for every button style. After changing a property at runtime, call `widget.style().unpolish(widget); widget.style().polish(widget)` to force QSS to re-evaluate.
- **Hover, pressed, focus, disabled — all four, every interactive element.** Qt applies `:hover`, `:pressed`, `:focus`, `:disabled` pseudo-states natively in QSS; there's no excuse to skip them. A visible focus border (`QPushButton:focus { border: 1px solid accent; }`) is not optional — this is a pointer-and-keyboard surface.
- **Resizable layouts only.** Use `QVBoxLayout`/`QHBoxLayout` with `addStretch()`, not fixed `setGeometry()` coordinates. Fix the sidebar width (`setFixedWidth`), let content stretch. Test by resizing the window narrower and wider.
- **Motion is limited and that's fine.** Native QSS pseudo-state changes (hover/pressed) are instant — Qt doesn't animate QSS transitions the way CSS does. For hover/selection feedback, instant is acceptable and matches "fast and functional." Only reach for `QPropertyAnimation` (on `windowOpacity`, `geometry`, or a custom animatable property) for deliberate moments like a panel opening or a dialog fading in — keep it to 100–150ms, ease-out, no bounce/spring.
- **Scrollbars are thin by default here** (`QScrollBar` styled to 8px, no arrow buttons, translucent thumb that darkens on hover) — see `theme.py`. True "hidden until scroll" behavior needs an event filter and is an optional enhancement, not required.
- **Icons:** keep one icon set and one stroke weight. If you need icon glyphs, `qtawesome` (`pip install qtawesome`) is the simplest way to get consistent Font Awesome / Material icons sized at 16–20px inside Qt widgets; don't mix filled and outline styles.
- **Switching PyQt6 ↔ PySide6:** `theme.py` only imports `QFont` from the binding; `demo_app.py` imports the rest. Swap `from PySide6.QtWidgets import ...` → `from PyQt6.QtWidgets import ...` (same for `QtCore`/`QtGui`) and `app.exec()` stays the same in both — no QSS or token changes needed.
- **Qt mnemonic gotcha:** a lone `&` in any `QGroupBox` title, `QPushButton` text, or buddy-linked `QLabel` text is consumed as a keyboard-accelerator marker, not displayed. `QGroupBox("Style & audio")` silently renders as `"Style  audio"` — no ampersand, a doubled space, no error or warning anywhere. This is easy to miss in code review because the source string looks correct. Never put a bare `&` in title/button/label text — spell it out (`"Style and audio"`) or escape it as `&&` if the literal character is required.

## Recommended patterns
- **Sidebar** (fixed 240px / `THEME.sidebar_width`): brand label, then nav buttons with `setProperty("nav", "true")` and `setCheckable(True)`, one checked at a time. Active item gets `accent_soft` background + `accent_pressed` text via the `:checked` selector — see `demo/demo_app.py::Sidebar`.
- **Toolbar** (fixed 52px / `THEME.toolbar_height`): view title on the left (`role="title"`), secondary controls (search, filters) and exactly one primary button on the right.
- **Cards**: `QFrame` with `setProperty("card", "true")` — hairline border, `radius_md`, `content_bg`. Use for stat tiles, grouped lists, settings sections.
- **Section dividers inside a card**: when a single card holds two logically distinct groups of controls (e.g. "pick a style" then "tune speed/pitch/volume"), separate them with a 1px `QFrame` rather than splitting into two cards:
  ```python
  divider = QFrame(self)
  divider.setObjectName("sectionDivider")
  divider.setFrameShape(QFrame.Shape.NoFrame)
  divider.setFixedHeight(1)   # set in Python, don't rely on QSS max-height alone
  layout.addWidget(divider)
  ```
  Style it via `QFrame#sectionDivider { background: border; border: none; }` in `theme.py`. Cheaper than a new card and keeps related controls visually grouped while still reading as two steps.
- **Settings columns / stacked cards** (e.g. a right-hand panel with several cards stacked vertically): give the column's own layout a single `setSpacing(THEME.space_3)` so every card-to-card gap is identical — don't hand-tune spacing per pair of cards. Align repeated label+control rows (like a set of sliders) by giving each row's label a shared `setMinimumWidth(...)` so the controls start at the same x-position instead of drifting with label text length.
- **List rows**: `QListWidget` with hover and `:selected` styled via `accent_soft` — see the QSS `QListWidget::item` block. Row height from `THEME.row_height` (42px comfortable).
- **One primary button per screen**, filled with the accent (`variant="primary"`). Every other action is `variant="secondary"` (bordered, neutral) or a plain nav-style button.

## Tuning knobs
- **Density**: this skill ships comfortable (14px body, 42px row height, 10px card radius) for a consumer app. For a compact/pro tool instead, drop to 13px body, 32px row height, 6px radius — same token names, different values.
- **Dark mode**: not in scope for this brief (light-only), but the token structure is dark-mode-ready — see the Color section above for the swap values if it's needed later.
- **Chrome style**: native OS title bar (default here, fastest, always correct) vs. fully custom frameless title bar (`Qt.FramelessWindowHint` + a draggable `QWidget` header with your own close/min/max buttons) — only take on the custom route if brand control over the window chrome is an explicit requirement.
- **Accent color**: swap `THEME.accent` to the project's brand color; everything else derives from it.

## Avoid
- Mobile patterns: bottom tab bars, oversized touch targets, full-bleed hero sections.
- Heavy `QGraphicsDropShadowEffect` on every card, or gradients as a primary surface fill — flat surfaces + hairline borders read as "native," not "web page in a window."
- A giant marketing-style headline in the content area — desktop apps open straight into the work.
- Skipping `:hover`/`:focus` QSS states "because it looks fine without them" — the pointer and keyboard are the primary input here, not touch.
- Fixed `setGeometry()` layouts that break the moment the window is resized — always use layout managers.
- Hardcoding a color or radius inline in a widget file instead of reading it from `THEME` — the first time you need to re-skin, this is what breaks.
- Mixing multiple accent colors, or using a second saturated color for anything other than a rare, deliberate warning/error/success state (and even then, keep those semantic colors separate from the brand accent).
- A literal `&` anywhere in a `QGroupBox` title, `QPushButton` label, or buddy-linked `QLabel` — see the mnemonic gotcha above. This is a silent bug, not a style nit: nothing errors, the text just renders wrong.
- Letting a hand-built card header (custom title `QLabel` + badge row) and a native `QGroupBox` title coexist in the same panel with different font sizes or weights — pin both to the same section-title spec so a stacked column of cards reads as one system, not two.

## Acceptance checks
- [ ] Every color, spacing, and radius value comes from `THEME.<token>`, not a hardcoded literal in widget code.
- [ ] Every interactive element (buttons, nav items, inputs, list rows) has a visible hover state and, where keyboard-focusable, a visible focus state.
- [ ] Only one accent color appears anywhere in the app.
- [ ] The window survives being resized narrower and wider without breaking the layout.
- [ ] Cards and panels use a 1px hairline border, not a drop shadow; shadows (if any) are reserved for menus/dialogs.
- [ ] No `QGroupBox` title, `QPushButton` label, or buddy-linked `QLabel` text contains an unescaped literal `&`.
- [ ] If the panel mixes custom card headers and native `QGroupBox` cards, every title renders at the same font size and weight.
- [ ] `python demo/demo_app.py` runs and visually matches `demo/screenshot.png`.

## Questions to ask (when the brief is vague)
- Does the project already have a brand accent color, or should it default to system blue (`#0A84FF`)?
- Is dark mode actually needed for v1, or is light-only (this skill's default) sufficient for now?
- Native OS title bar, or full custom chrome? (Default: native — faster, always correct.)
- Any existing screens/widgets to retrofit, or a clean new app shell?