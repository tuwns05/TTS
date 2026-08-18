Desktop Qt UI Designer

Mission

Create desktop software that looks intentional, modern, clean, professional, native-feeling, and comfortable to use for long sessions.

The goal is not to make Qt look like a web page. The goal is to build a coherent desktop product with strong hierarchy, predictable interactions, useful feedback, and maintainable UI code.

When working in an existing repository, improve the interface without breaking business logic, threading, model lifecycle, audio behavior, persistence, or application architecture.

1. First rule: inspect the project before changing UI

Before writing or editing UI code:

Detect the Qt binding already used by the project.

Inspect the existing design system/theme before inventing a new one.

Inspect the main application shell and navigation.

Identify where business logic lives.

Identify long-running operations and how they are moved off the UI thread.

Reuse existing widgets, helpers, resources, and conventions whenever they are sound.

Do not rewrite a working UI architecture merely to make a visual change.

Binding detection

If the project imports:

from PySide6 ...

continue using PySide6.

If the project imports:

from PyQt6 ...

continue using PyQt6.

Never mix PySide6 and PyQt6 imports in the same application.

Do not migrate from one binding to the other unless the user explicitly asks for a migration.

Signal compatibility

PySide6:

from PySide6.QtCore import Signal, Slot

PyQt6:

from PyQt6.QtCore import pyqtSignal, pyqtSlot

Do not blindly replace one with the other.

2. Project-specific context: tuwns05/TTS

When this skill is used in the TTS repository, assume the current architecture is intentional unless evidence shows otherwise.

Repository UI area:

src/vntts/
├── config/
│   └── theme.py
├── ui/
│   ├── main_window.py
│   ├── compose_view.py
│   ├── controls.py
│   ├── fonts.py
│   ├── settings_panel.py
│   └── voice_clone_view.py
├── services/
├── engines/
└── utils/

Current application characteristics:

PySide6 Qt Widgets application.

QMainWindow is the desktop shell.

Sidebar navigation switches pages through QStackedWidget.

Main pages include:

Tạo giọng nói / speech composition.

Nhân bản giọng / voice cloning.

Cài đặt model / model settings.

Page content is wrapped in scroll areas where needed.

The compose workspace already reflows between wide, compact, and narrow modes.

TTS synthesis and other expensive work are executed outside the GUI thread.

Audio playback and waveform controls already exist.

Design tokens and global QSS live in src/vntts/config/theme.py.

Existing components use object names and dynamic properties such as role, variant, nav, card, and state for styling.

Preserve these boundaries

UI code may:

render state;

emit user intents;

validate simple presentation-level input;

update visual state;

arrange widgets;

connect signals;

trigger ViewModel/service commands through the existing interfaces.

UI code should not absorb:

TTS engine implementation;

model loading internals;

persistence rules;

audio processing algorithms;

hardware detection logic;

business workflows already owned by services/ViewModels.

Do not move long-running work back onto the main Qt event loop.

3. Default visual direction

If the user only says "make the desktop UI beautiful", "modernize the UI", or similar and gives no visual system, use this default:

Modern native desktop / calm productivity UI

Characteristics:

Windows 10/11 friendly.

Native title bar unless custom chrome is explicitly requested.

Light theme by default for the current TTS app.

Neutral surfaces.

One restrained accent color.

Clear content hierarchy.

Comfortable density rather than oversized mobile-style controls.

Soft but restrained corner radii.

Thin borders instead of heavy shadows.

No decorative gradients unless the product identity explicitly requires them.

No glassmorphism by default.

No giant marketing-style hero text.

No unnecessary animations.

No "website inside a window" appearance.

A desktop application should open directly into useful work.

4. Design system is mandatory

Never scatter visual constants across widget files.

Use a centralized token system.

For the TTS repo, extend and reuse:

src/vntts/config/theme.py

Do not replace it with inline setStyleSheet() fragments unless a widget has a truly isolated rendering requirement that QSS cannot express.

Token categories

A theme should define at minimum:

Surfaces

window_bg
panel_bg
content_bg
overlay_bg
border
border_strong

Text

text_primary
text_secondary
text_muted
text_disabled
text_on_accent

Interactive

accent
accent_hover
accent_pressed
accent_soft
focus_ring

Semantic state

success
success_soft
warning
warning_soft
error
error_soft
info
info_soft

Use semantic colors for status only. Do not introduce several unrelated saturated colors as decoration.

Radius

Recommended desktop scale:

radius_sm = 6
radius_md = 10
radius_lg = 12

Avoid using 20-32 px radii everywhere. Excessively rounded surfaces read like mobile cards rather than desktop controls.

Spacing

Use a small consistent scale:

4, 8, 12, 16, 24, 32

Do not invent arbitrary values such as 13, 19, 27, 31 unless a technical constraint requires them.

Typography

For the existing TTS visual system, a practical hierarchy is:

caption/meta    11-12
body            14
section         15-16
page title      20-24

Use only 3-4 active text sizes on one screen.

Prefer the operating-system UI font.

On Windows, use Segoe UI / the system UI font through QFont rather than importing a random web font.

Typography hierarchy should come primarily from:

size;

weight;

spacing;

text color;

not from excessive capitalization or decorative effects.

5. QSS architecture

Apply the global stylesheet once at application level whenever possible:

app.setStyleSheet(build_stylesheet(THEME))

Use dynamic properties to represent reusable variants.

Examples:

button.setProperty("variant", "primary")
button.setProperty("nav", True)
card.setProperty("card", True)
label.setProperty("role", "section")
status.setProperty("state", "success")

Then style them centrally:

QPushButton[variant="primary"] { ... }
QPushButton[nav="true"] { ... }
QFrame[card="true"] { ... }
QLabel[role="section"] { ... }
QLabel[state="success"] { ... }

When a dynamic property changes at runtime, refresh QSS safely:

widget.style().unpolish(widget)
widget.style().polish(widget)
widget.update()

Do not create a new QPushButton subclass solely because it needs a different color.

6. Layout rules

Always use Qt layouts

Use:

QVBoxLayout

QHBoxLayout

QGridLayout

QFormLayout when appropriate

QBoxLayout when direction must change dynamically

QStackedWidget for major page navigation

QScrollArea for content that must survive reduced height/width

QSplitter only when user-adjustable panel sizing is genuinely useful

Avoid manual setGeometry() for normal application layout.

Avoid absolute positioning.

Fixed width/height should be reserved for structural elements where a stable metric is intentional, such as:

sidebar width;

toolbar height;

icon button size;

waveform minimum height;

small status badges.

Responsive desktop behavior

Desktop windows resize. Design for it.

For the TTS application, preserve and improve the existing wide / compact / narrow behavior rather than replacing it with a fixed layout.

Recommended behavior:

Wide

Sidebar remains visible.

Main compose area and settings/options can appear side by side.

Text editor receives the largest share of space.

Secondary controls remain compact.

Audio player stays readable without dominating the screen.

Compact

Main content becomes vertically stacked where necessary.

Header actions can remain horizontal if they still fit comfortably.

Settings cards use full available width.

Avoid horizontal scrolling.

Narrow

Stack header groups vertically.

Stack player controls and metadata where needed.

Allow vertical scrolling.

Preserve the primary action.

Do not shrink text or controls until they become uncomfortable.

Responsive behavior should change layout structure, not merely reduce font size.

7. Information hierarchy for the TTS application

The primary user journey is:

Enter text
→ choose/configure voice
→ generate speech
→ listen
→ export

The interface should visually reinforce that order.

Compose / Tạo giọng nói page

Priority order:

Text input.

Voice selection.

Main synthesis action.

Essential voice/style controls.

Generation status/progress.

Playback waveform and transport controls.

Export actions.

Secondary technical/model details.

Do not give every card equal visual weight.

The synthesis button should normally be the single strongest action on the page.

Playback/export actions become visually important only after audio exists.

Text editor

Give it generous space.

Make placeholder/help copy secondary.

Character count or input validation should not compete with the text.

Import-document action should be discoverable but secondary to direct text input.

Long text should scroll naturally.

Voice/model controls

Group controls by user intent, not by implementation class.

Good grouping:

Voice
├── voice selection
├── speech style
└── speed/pitch/volume

Technical runtime information should remain secondary unless the user opens Settings.

Synthesis state

Never leave the user unsure whether work started.

Possible states:

idle
ready
loading_engine
importing_document
synthesizing
enrolling_voice
success
error

For a long synthesis operation:

disable conflicting actions;

keep cancel/stop available when technically supported;

show a clear textual state;

show progress when meaningful progress data exists;

do not freeze the window;

do not replace the entire page with a blocking modal.

Audio/player area

The audio area should behave like a compact desktop player:

Play/Pause   Stop   00:12 ─── waveform ─── 01:37   Export

Rules:

waveform is functional, not decorative;

seek behavior remains obvious;

elapsed and total duration align consistently;

disabled state is clear before audio exists;

export WAV/MP3 actions are secondary controls;

do not use oversized circular mobile-player buttons unless specifically requested.

Voice Clone page

User journey:

Name profile
→ choose reference audio
→ validate sample
→ create profile
→ preview/use profile

Separate:

create-new-profile workflow;

existing profile management.

Existing profile list should show useful state at a glance and expose destructive actions carefully.

Deleting a voice profile should require confirmation if it cannot be trivially restored.

Sample guidance should be concise and visually secondary.

Model Settings page

This is a settings screen, not a dashboard.

Use a simple vertical hierarchy:

Page title
Short explanation
Model selection
Device selection
Runtime/current model summary
Load/apply action
Status/error information

Avoid filling the page with decorative cards.

Use progressive disclosure for technical details.

8. Component styling rules

Buttons

Use a small variant system.

Primary

Use for the main action of the current screen/group.

Examples:

Tạo giọng nói

Load model

Tạo hồ sơ giọng

Properties:

button.setProperty("variant", "primary")

Secondary

Neutral bordered or low-emphasis button.

Examples:

Import file

Export WAV

Export MP3

Browse

Ghost / toolbar

For low-emphasis actions or compact icon/text buttons.

Destructive

Use semantic error color only for destructive operations.

Examples:

Xóa hồ sơ

Remove model

Never make ordinary Cancel buttons red.

Required states

Every interactive button needs appropriate states:

default;

hover;

pressed;

keyboard focus;

disabled;

checked/selected when relevant.

A disabled button must still be readable but clearly inactive.

Inputs

Inputs should have:

clear label;

neutral border;

visible focus border/ring;

readable placeholder;

disabled state;

error state when needed.

Do not rely on placeholder text as the only label for important fields.

Combo boxes

For the current project, reuse ChevronComboBox when appropriate instead of creating a second custom combo implementation.

Keep popup row height comfortable and consistent.

Do not hide selection state.

Sliders

label every slider;

show current value if the value matters to the user;

use a thin track;

use a clearly draggable handle;

maintain keyboard support;

keep repeated slider labels aligned.

Cards

Use cards only when a visible boundary helps explain grouping.

A card should generally use:

content background;

1 px border;

moderate radius;

no heavy shadow.

Do not wrap every 2 controls in a separate card.

Prefer spacing and section dividers for related controls inside the same logical group.

Status badges

Badges should be compact and semantic.

Examples:

Sẵn sàng
Đang tải model
Đang tổng hợp
Hoàn tất
Lỗi
CPU
GPU

Color must not be the only indication of meaning. Keep readable text.

Lists

For voice profiles and similar lists:

consistent row height;

clear hover;

clear selected state;

selected row should remain readable;

destructive action should not dominate each row;

use empty-state text when there are no entries.

9. Icons

Use one coherent icon family.

Priority:

existing project icons/resources;

Qt standard icons if visually suitable;

a bundled SVG set with consistent stroke/style;

an additional icon library only when the project explicitly accepts the dependency.

Do not mix random Unicode symbols, emoji, filled icons, outline icons, and system icons in the same toolbar.

Typical desktop icon sizes:

16 px compact controls
18 px standard controls
20 px prominent toolbar controls

Use icons to aid recognition, not replace every label.

Actions such as Save, Play, Stop, Delete, Settings, Browse may use icons, but important or ambiguous actions should retain text/tooltips.

10. Accessibility and keyboard UX

Desktop UI must not be mouse-only.

Required:

logical Tab order;

visible keyboard focus;

Escape closes dismissible dialogs/popovers where appropriate;

Enter/Return activates the expected default action where safe;

accessible names for icon-only or ambiguous controls;

readable contrast;

state conveyed by text/icon plus color, not color alone;

no keyboard traps.

Use:

widget.setAccessibleName("...")
widget.setAccessibleDescription("...")

when the visible label is insufficient.

Do not remove focus borders without adding a proper replacement.

11. Loading, progress, errors, empty states

A polished application explicitly designs non-happy-path states.

For every asynchronous feature, consider:

idle
loading
success
error
empty
disabled
partial result
cancelled

Feedback timing

If work is effectively instant, no special loader is required.

If an operation becomes perceptible, immediately show state feedback.

If an operation takes several seconds, show persistent progress/status rather than relying only on the mouse cursor.

If real percentage progress exists, prefer QProgressBar with real progress.

If progress is indeterminate, use a compact indeterminate progress indicator or textual busy state without blocking the entire UI.

For TTS synthesis, users should always see that synthesis is running and should be prevented from starting conflicting synthesis operations.

Error UX

Error messages should explain:

what failed;

what the user can do next.

Bad:

Error 500

Better:

Không thể tải model trên GPU. Ứng dụng vẫn có thể thử lại bằng CPU.

Preserve technical details in logs or an expandable details area when useful; do not dump stack traces into the main UI.

Empty state

An empty voice-profile list should not appear broken.

Show concise guidance, e.g.:

Chưa có hồ sơ giọng.
Tạo hồ sơ đầu tiên từ một mẫu âm thanh rõ ràng.

12. Desktop interaction and motion

Motion should explain state change, not decorate the screen.

Qt Widgets does not need CSS-style animation everywhere.

Use instant native feedback for:

hover;

press;

focus;

selection.

Use QPropertyAnimation only for deliberate transitions such as:

expanding/collapsing an optional panel;

fading a transient notification;

sliding a small contextual drawer.

Recommended durations:

small feedback: 100-150 ms
panel transition: 150-250 ms

Avoid bounce/spring effects in a productivity desktop tool.

Never animate layout constantly during TTS processing.

13. Light and dark themes

For the current TTS project, preserve light mode unless the task asks for dark mode or theme switching.

If adding dark mode:

Keep the same token names.

Create a dark token set instead of scattering conditional colors through widgets.

Rebuild/apply the global stylesheet when the theme changes.

Test waveform, focus, disabled, badges, menus, combo popups, dialogs, and selection states in both themes.

Persist the user's choice through the project's existing settings mechanism.

Widget code should not contain logic such as:

if dark_mode:
    button.setStyleSheet("background: #222")
else:
    button.setStyleSheet("background: #fff")

Put theme differences in the token/QSS layer.

14. High-DPI and Windows desktop behavior

Design for typical Windows scaling such as 100%, 125%, and 150%.

Rules:

prefer layouts over coordinates;

avoid drawing text at hardcoded pixel positions;

do not assume a fixed monitor resolution;

allow labels to expand;

test long Vietnamese strings;

do not truncate important action labels;

use QSizePolicy intentionally;

avoid forcing large fixed heights on text containers;

use screen-aware sizing only when truly needed.

Vietnamese text can be longer than equivalent English labels; leave room for expansion.

15. PySide6 / PyQt6 implementation quality

Keep GUI thread responsive

Never run model loading, synthesis, inference, file decoding, or expensive audio processing directly inside a button click handler on the GUI thread.

Use the project's existing worker abstraction, QThreadPool, QRunnable, QThread, or service/ViewModel async mechanism as appropriate.

For the TTS repo, prefer the existing worker/ViewModel patterns instead of adding a parallel threading architecture.

Signal-driven updates

Worker/service result should return to UI through Qt-safe signal/state paths.

Avoid manipulating widgets directly from a worker thread.

Parent ownership

Give widgets sensible Qt parents and avoid unnecessary lifetime complexity.

Object names

Use stable objectName values for:

QSS targeting;

automated UI tests;

debugging.

Do not rename existing object names casually if tests or styling may depend on them.

Custom painting

Use custom QPainter widgets when the visual is inherently custom, such as the waveform.

For ordinary controls, prefer standard widgets + QSS instead of painting your own button/input implementation.

16. Refactoring rules for an existing UI

When improving an existing application:

Prefer

extract repeated widget construction;

centralize duplicated spacing/colors;

reuse theme tokens;

reduce visual inconsistency;

simplify nested layouts;

add missing states;

improve naming;

preserve public widget interfaces when possible.

Avoid

rewriting entire screens for a small visual request;

moving service logic into widgets;

changing engine behavior while styling UI;

renaming signals without need;

introducing a second theme system;

replacing working custom widgets without a clear benefit;

adding large dependencies just for one visual effect.

Keep the diff focused.

17. Design audit workflow

When asked to improve an existing screen, perform this audit before editing:

A. Hierarchy

Check:

Is the main action obvious?

Is the page title stronger than section headings?

Are secondary details visually quieter?

Are important states visible?

B. Spacing

Check:

Are outer margins consistent?

Are card gaps consistent?

Are label/control gaps consistent?

Are unrelated groups sufficiently separated?

C. Alignment

Check:

Do repeated fields align?

Do buttons in the same group share height?

Do card titles align?

Do status labels drift unpredictably?

D. Components

Check:

button variants;

inputs;

combo boxes;

sliders;

list rows;

badges;

scrollbars;

dialogs;

empty/loading/error states.

E. Responsiveness

Test:

wide window;

medium window;

narrow window;

short-height window;

scroll behavior.

F. Interaction

Test:

hover;

press;

focus;

disabled;

keyboard navigation;

long-running operation;

error path.

G. Consistency

Check for:

hardcoded colors;

one-off radii;

random font sizes;

duplicate stylesheets;

mixed icon styles;

inconsistent Vietnamese terminology.

18. Workflow when implementing a UI task

Follow this sequence.

Step 1 — Inspect

Read the relevant screen plus:

src/vntts/config/theme.py
src/vntts/ui/main_window.py
src/vntts/ui/controls.py

and the page-specific file.

Step 2 — Identify the user journey

State in one sentence what the user is trying to accomplish on the screen.

Use that to decide visual priority.

Step 3 — Reuse the current system

Before creating anything new, check whether the project already has:

a component;

a theme token;

a dynamic property;

a layout pattern;

a worker mechanism;

an object-name convention.

Step 4 — Implement the smallest coherent improvement

Change only what supports the requested design improvement.

If the theme lacks a needed reusable concept, add a token/QSS selector first, then use it in the widget.

Step 5 — Verify states

At minimum verify:

default
hover
focus
disabled
loading/busy
success
error

where relevant.

Step 6 — Verify resizing

Test all project breakpoints and make sure no important controls disappear or overlap.

Step 7 — Verify behavior

Do not consider the UI finished if it looks better but synthesis, playback, model loading, or voice enrollment regressed.

19. Testing for the TTS repository

After UI changes, run the most relevant existing tests.

Typical development verification:

python -m pytest

Run the application when possible:

python -m vntts

For a visual change, manually verify at least:

Tạo giọng nói page opens;

Nhân bản giọng page opens;

Cài đặt page opens;

sidebar selected state updates;

window can resize;

scroll areas work;

synthesis controls still enable/disable correctly;

playback controls still work when audio exists;

theme/QSS has no broken selectors;

no uncaught Qt warnings/errors are introduced by the change.

If a test already exists for an object name or widget state, preserve it or update it only when the product behavior intentionally changed.

20. Things to avoid

Do not produce these common AI-generated UI problems:

giant rounded cards everywhere;

gradients on every primary surface;

neon colors;

glassmorphism without a product reason;

huge shadows around every card;

random emoji icons;

four different accent colors;

huge 30-40 px headings in a desktop work screen;

excessive explanatory text;

mobile bottom navigation inside a Windows app;

fixed setGeometry() layouts;

web-style hamburger menus when a persistent desktop sidebar fits;

a loader that blocks the whole app for normal background work;

changing font size to solve responsiveness;

inline QSS repeated in many widgets;

rebuilding an existing component from scratch because it is easier for the AI;

visually hiding disabled controls so the user cannot understand available features;

destructive buttons styled like normal primary actions;

color-only error/success indicators;

putting every setting into the main compose screen;

mixing PySide6 and PyQt6.

21. Decision defaults

When requirements are vague, do not stop implementation for cosmetic questions that can be safely inferred.

Use these defaults:

Platform: Windows 10/11 desktop
Binding: existing project binding
TTS repo binding: PySide6
Window chrome: native OS title bar
Theme: existing project theme / light mode
Style: minimal, professional, native-feeling
Accent: existing project accent
Density: comfortable desktop
Navigation: existing sidebar + stacked pages
Layout: resizable and responsive
Icons: existing coherent icon source
Animation: minimal and functional
Architecture: preserve existing ViewModel/services/workers

Ask only when the missing answer would materially change product behavior or architecture.

22. Definition of "beautiful" for this skill

A beautiful desktop UI is not the one with the most decoration.

It should feel:

clear;

calm;

fast;

deliberate;

consistent;

trustworthy;

easy to scan;

easy to operate with mouse and keyboard;

stable while resizing;

responsive during long operations;

visually coherent across every page.

Users should notice the task, not the styling tricks.

23. Acceptance checklist

Before considering a UI task complete, verify:

The project uses only one Qt binding.

Existing TTS business logic and services were not moved into UI code.

Long-running operations do not block the main GUI thread.

Existing theme tokens/QSS are reused or extended instead of bypassed.

No unnecessary hardcoded colors/radii are added to widget files.

Page hierarchy has one obvious primary task/action.

Spacing follows a consistent scale.

Typography uses a small coherent hierarchy.

Cards are used for grouping, not decoration.

Buttons expose hover, pressed, focus, and disabled states where relevant.

Inputs expose visible focus and error states where relevant.

Status is communicated with text/icon plus color, not color alone.

Empty/loading/error states are designed.

The window works in wide, compact, and narrow layouts where applicable.

Important content does not require horizontal scrolling.

Keyboard navigation remains usable.

Existing object names relied on by QSS/tests are preserved unless intentionally changed.

Sidebar/page navigation still works.

Playback/waveform behavior still works.

Voice clone flow still works.

Model settings flow still works.

Relevant tests pass.

The UI looks like a desktop application, not a marketing website or mobile screen.

24. Expected agent behavior

When asked to design or refactor UI, do not only describe what should be changed.

When code changes are requested and repository access is available:

inspect the real files;

implement the change in the existing architecture;

update theme tokens/QSS when needed;

preserve runtime behavior;

run relevant tests;

report the files changed and the user-visible result.

If the request is specifically for a visual audit, provide findings ordered by impact:

Critical usability issue
Major inconsistency
Visual polish improvement
Optional enhancement

Never trade functional correctness for visual polish.