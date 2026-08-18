"""
theme.py — Design tokens + QSS builder for minimal-pyqt-desktop-app-ui.

Drop this file into your project (e.g. `app/theme.py`) and:

    from theme import THEME, build_stylesheet, get_system_font

    app = QApplication(sys.argv)
    app.setFont(get_system_font())
    app.setStyleSheet(build_stylesheet(THEME))

Every color, spacing, and radius value lives here as a single source of
truth. Never hardcode a color or a pixel radius inside a widget file —
import it from THEME instead. This is what makes re-skinning, theming,
and consistency actually work.

Works with PySide6 (default import below) and PyQt6 — see the two lines
marked "PyQt6" if you need to switch bindings.

GOTCHA — Qt mnemonics: a lone "&" inside any QGroupBox title, QPushButton
text, or buddy-linked QLabel text is treated as a keyboard-shortcut marker
and silently consumed at render time. `QGroupBox("Style & audio")` renders
as "Style  audio" — no ampersand, a doubled space, and no visible bug in
the source. Never put a bare "&" in title/button/label text; spell it out
("Style and audio") or escape it as "&&" if the literal character is
unavoidable.
"""

import platform
from dataclasses import dataclass

# --- Qt binding -------------------------------------------------------
# Default: PySide6. To use PyQt6 instead, comment the PySide6 line and
# uncomment the PyQt6 line — the rest of this file is binding-agnostic.
from PySide6.QtGui import QFont  # PyQt6: from PyQt6.QtGui import QFont

# --- Design tokens ------------------------------------------------------

@dataclass(frozen=True)
class Theme:
    # Surfaces (light mode, comfortable/consumer density)
    window_bg: str = "#F5F5F7"      # outermost window background
    panel_bg: str = "#FAFAFA"       # sidebar / toolbar background
    content_bg: str = "#FFFFFF"     # main content surface, cards
    border: str = "#E5E5EA"         # hairline border between surfaces
    border_strong: str = "#C7C7CC"  # emphasized input/card boundary
    overlay_bg: str = "#FFFFFF"     # menus, popovers, dialogs (elevated)

    # Text
    text_primary: str = "#1D1D1F"
    text_secondary: str = "#6E6E73"
    text_muted: str = "#8E8E93"
    text_on_accent: str = "#FFFFFF"
    text_disabled: str = "#B9B9BE"

    # Accent — one color only. Used for primary action, selection,
    # active nav item. Never introduce a second saturated color.
    accent: str = "#0A84FF"
    accent_hover: str = "#3396FF"
    accent_pressed: str = "#0868CC"
    accent_soft: str = "rgba(10, 132, 255, 0.12)"    # selection / active-nav bg
    focus_ring: str = "#0A84FF"

    # Semantic state colors
    success: str = "#248A3D"
    success_soft: str = "rgba(36, 138, 61, 0.12)"
    warning: str = "#A05A00"
    warning_soft: str = "rgba(160, 90, 0, 0.12)"
    error: str = "#D70015"
    error_soft: str = "rgba(215, 0, 21, 0.10)"
    info: str = "#0868CC"
    info_soft: str = "rgba(10, 132, 255, 0.12)"

    # Radius (comfortable/consumer: softer than a "technical" 6px)
    radius_sm: int = 6     # inputs, small buttons, list rows
    radius_md: int = 10    # cards, panels, dialogs
    radius_lg: int = 12    # large surfaces / modals

    # Spacing scale (px) — use these, don't invent one-off values
    space_1: int = 4
    space_2: int = 8
    space_3: int = 12
    space_4: int = 16
    space_5: int = 24
    space_6: int = 32

    # Typography (comfortable density: 14px body, not 13px compact)
    font_size_caption: int = 11
    font_size_body: int = 14
    font_size_section: int = 15
    font_size_title: int = 22

    # Layout metrics
    sidebar_width: int = 200
    toolbar_height: int = 52
    row_height: int = 42          # comfortable row height (32px = compact)
    combo_arrow_size: int = 8
    combo_popup_row_height: int = 38
    combo_max_visible_items: int = 8
    icon_size: int = 18
    content_reading_width: int = 760
    clone_profile_row_height: int = 84
    clone_profile_list_max_rows: int = 4
    narrow_content_breakpoint: int = 620
    control_stroke_width: float = 1.5
    slider_track_height: int = 4
    slider_handle_size: int = 14
    slider_handle_border: int = 2

    # Motion (reference only — see SKILL.md "Motion" section for how
    # to actually animate hover/selection changes in Qt)
    motion_ms: int = 150


THEME = Theme()


# --- System font stack ---------------------------------------------------

def get_system_font(theme: Theme = THEME) -> QFont:
    """Return the native OS UI font at the theme's body size.

    Qt does not support CSS-style font-family fallback lists in QFont,
    so pick per-platform rather than relying on QSS font-family alone.
    """
    system = platform.system()
    if system == "Darwin":
        family = ".AppleSystemUIFont"   # resolves to San Francisco
    elif system == "Windows":
        family = "Segoe UI"
    else:
        family = "Ubuntu"               # falls back gracefully on most distros
    font = QFont(family, theme.font_size_body)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


# --- QSS builder ----------------------------------------------------------

def build_stylesheet(t: Theme = THEME) -> str:
    """Build the global application QSS from the token set above.

    Apply once at the QApplication level (app.setStyleSheet(...)).
    Per-widget one-off styles should still reference `t.<token>` rather
    than hardcoding a value, so a future re-theme stays a one-file change.
    """
    return f"""
    /* ---------- Base ---------- */
    QMainWindow, QDialog {{
        background: {t.window_bg};
    }}
    QWidget {{
        color: {t.text_primary};
        font-size: {t.font_size_body}px;
    }}
    QLabel[role="secondary"] {{
        color: {t.text_secondary};
    }}
    QLabel[role="title"] {{
        font-size: {t.font_size_title}px;
        font-weight: 600;
    }}
    QLabel[role="section"] {{
        font-size: {t.font_size_section}px;
        font-weight: 600;
    }}
    QLabel#activeModelTitle {{
        color: {t.success};
        font-size: {t.font_size_section}px;
        font-weight: 700;
    }}
    QLabel[role="caption"] {{
        font-size: {t.font_size_caption}px;
        color: {t.text_secondary};
    }}
    QLabel#fieldLabel {{
        font-weight: 500;
    }}

    /* ---------- Sidebar ---------- */
    QFrame#sidebar {{
        background: {t.panel_bg};
        border-right: 1px solid {t.border};
    }}
    QPushButton[nav="true"] {{
        text-align: left;
        padding: {t.space_2}px {t.space_3}px;
        border: none;
        border-radius: {t.radius_sm}px;
        background: transparent;
        color: {t.text_primary};
        font-weight: 500;
    }}
    QPushButton[nav="true"]:hover {{
        background: rgba(0, 0, 0, 0.04);
    }}
    QPushButton[nav="true"]:checked {{
        background: {t.accent_soft};
        color: {t.accent_pressed};
    }}

    /* ---------- Toolbar ---------- */
    QFrame#toolbar {{
        background: {t.panel_bg};
        border-bottom: 1px solid {t.border};
    }}

    /* ---------- Content / cards ---------- */
    QWidget#content {{
        background: {t.window_bg};
    }}
    QFrame[card="true"], QWidget[card="true"] {{
        background: {t.content_bg};
        border: 1px solid {t.border};
        border-radius: {t.radius_md}px;
    }}
    QFrame[fileSelector="true"] {{
        background: {t.panel_bg};
        border: 1px solid {t.border_strong};
        border-radius: {t.radius_sm}px;
    }}
    QFrame[fileSelector="true"][hasFile="true"] {{
        background: {t.info_soft};
        border-color: {t.accent};
    }}
    QLabel#voiceSampleFileName {{
        background: transparent;
        border: none;
        font-weight: 500;
    }}
    QFrame[emptyState="true"] {{
        background: {t.panel_bg};
        border: 1px solid {t.border};
        border-radius: {t.radius_sm}px;
    }}
    QWidget[settingsSection="true"], QGroupBox[settingsSection="true"] {{
        background: transparent;
        border: none;
        border-radius: 0;
    }}
    QGroupBox[settingsSection="true"] {{
        margin-top: {t.space_3}px;
    }}
    QGroupBox[settingsSection="true"]::title {{
        left: 0;
        padding: 0 {t.space_1}px;
    }}

    /* QGroupBox itself carries NO font-weight — that used to cascade
       down into every child (combo boxes, labels) and silently bold
       content that should stay regular. Bold belongs on the title
       chip only, via QGroupBox::title below. */
    QGroupBox {{
        background: {t.content_bg};
        border: 1px solid {t.border};
        border-radius: {t.radius_md}px;
        margin-top: {t.space_3}px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: {t.space_3}px;
        padding: 0 {t.space_1}px;
        color: {t.text_primary};
        font-size: {t.font_size_section}px;
        font-weight: 600;
    }}
    /* If a panel also has a hand-built card header (title QLabel +
       badge in a QHBoxLayout, e.g. an "Engine" selector), give that
       title QLabel role="section" so it resolves to the exact same
       font-size/weight as QGroupBox::title above. Two different title
       mechanisms rendering two different sizes is the #1 way a
       stacked-card settings panel ends up looking inconsistent. */

    /* ---------- Section dividers (inside a card) ---------- */
    /* A thin 1px rule used to separate two logical groups of controls
       WITHIN the same card, without spawning a second card. In Python:
           divider = QFrame(self)
           divider.setObjectName("sectionDivider")
           divider.setFrameShape(QFrame.Shape.NoFrame)
           divider.setFixedHeight(1)
       Set the fixed height in Python, not just via QSS max-height —
       relying on QSS alone here is inconsistent across styles. */
    QFrame#sectionDivider {{
        background: {t.border};
        border: none;
    }}

    /* ---------- Buttons ---------- */
    QPushButton {{
        border-radius: {t.radius_sm}px;
        padding: {t.space_2}px {t.space_4}px;
        font-weight: 500;
        background: {t.content_bg};
        color: {t.text_primary};
        border: 1px solid {t.border};
    }}
    QPushButton:hover {{
        background: rgba(0, 0, 0, 0.03);
    }}
    QPushButton:pressed {{
        background: {t.accent_soft};
    }}
    QPushButton:disabled {{
        color: {t.text_disabled};
        background: {t.panel_bg};
    }}
    QPushButton[variant="primary"] {{
        background: {t.accent};
        color: {t.text_on_accent};
        border: none;
    }}
    QPushButton[variant="primary"]:hover {{
        background: {t.accent_hover};
    }}
    QPushButton[variant="primary"]:pressed {{
        background: {t.accent_pressed};
    }}
    QPushButton[variant="primary"]:disabled {{
        background: {t.text_disabled};
        color: {t.overlay_bg};
    }}
    QPushButton[variant="secondary"] {{
        background: {t.content_bg};
        color: {t.text_primary};
        border: 1px solid {t.border};
    }}
    QPushButton[variant="secondary"]:hover {{
        background: rgba(0, 0, 0, 0.03);
    }}
    QPushButton[variant="ghost"] {{
        background: transparent;
        color: {t.text_secondary};
        border: none;
        padding-left: {t.space_2}px;
        padding-right: {t.space_2}px;
    }}
    QPushButton[variant="ghost"]:hover {{
        background: {t.error_soft};
        color: {t.error};
    }}
    QPushButton#resetVoiceStyleButton {{
        background: {t.content_bg};
        color: {t.text_secondary};
        padding: {t.space_1}px {t.space_2}px;
    }}
    QPushButton#resetVoiceStyleButton:hover {{
        background: {t.accent_soft};
        color: {t.accent};
    }}
    QPushButton[variant="destructive"] {{
        background: {t.content_bg};
        color: {t.error};
        border: 1px solid {t.error};
    }}
    QPushButton[variant="destructive"]:hover {{
        background: {t.error_soft};
    }}
    QPushButton:focus {{
        outline: none;
        border: 1px solid {t.accent};
    }}

    /* ---------- Inputs ---------- */
    QLineEdit, QComboBox, QTextEdit, QPlainTextEdit {{
        background: {t.content_bg};
        border: 1px solid {t.border};
        border-radius: {t.radius_sm}px;
        padding: {t.space_2}px {t.space_3}px;
        selection-background-color: {t.accent_soft};
    }}
    QComboBox {{
        padding-right: {t.space_6}px;
    }}
    QComboBox:hover {{
        background: rgba(0, 0, 0, 0.02);
    }}
    QComboBox:disabled {{
        color: {t.text_disabled};
        background: {t.panel_bg};
    }}
    QComboBox::drop-down {{
        border: none;
        width: {t.space_6}px;
    }}
    QComboBox::down-arrow {{
        image: none;
        width: 0;
        height: 0;
    }}
    QComboBox QAbstractItemView {{
        background: {t.overlay_bg};
        border: 1px solid {t.border};
        border-radius: {t.radius_sm}px;
        outline: 0;
        padding: {t.space_1}px;
        show-decoration-selected: 1;
        selection-background-color: {t.accent_soft};
        selection-color: {t.accent_pressed};
    }}
    QComboBox QAbstractItemView::item {{
        min-height: {t.combo_popup_row_height}px;
        padding: 0 {t.space_2}px;
        border: none;
        border-radius: {t.radius_sm}px;
    }}
    QComboBox QAbstractItemView::item:hover {{
        background: rgba(0, 0, 0, 0.04);
    }}
    QComboBox QAbstractItemView::item:selected {{
        background: {t.accent_soft};
        color: {t.accent_pressed};
    }}
    QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {t.accent};
    }}

    QLabel#engineStatus, QLabel#statusLabel, QLabel#engineBadge,
    QLabel#profileStatusLabel {{
        color: {t.text_secondary};
        background: {t.panel_bg};
        border-radius: {t.radius_sm}px;
        padding: {t.space_1}px {t.space_2}px;
        font-size: {t.font_size_caption}px;
        font-weight: 500;
    }}
    QLabel#engineStatus[state="busy"], QLabel#statusLabel[state="busy"],
    QLabel#profileStatusLabel[state="busy"] {{
        color: {t.info};
        background: {t.info_soft};
    }}
    QLabel#engineStatus[state="success"], QLabel#statusLabel[state="success"],
    QLabel#engineBadge[state="success"], QLabel#profileStatusLabel[state="success"] {{
        color: {t.success};
        background: {t.success_soft};
    }}
    QLabel#engineStatus[state="error"], QLabel#statusLabel[state="error"],
    QLabel#profileStatusLabel[state="error"] {{
        color: {t.error};
        background: {t.error_soft};
    }}
    QLabel#engineStatus[state="warning"], QLabel#statusLabel[state="warning"],
    QLabel#profileStatusLabel[state="warning"] {{
        color: {t.warning};
        background: {t.warning_soft};
    }}
    QLabel[profileState="true"] {{
        color: {t.success};
        background: transparent;
        border: none;
        font-size: {t.font_size_caption}px;
    }}

    QSlider::groove:horizontal {{
        height: {t.slider_track_height}px;
        border-radius: {t.slider_track_height // 2}px;
        background: {t.border};
    }}
    QSlider::sub-page:horizontal {{
        background: {t.accent_pressed};
        border-radius: {t.slider_track_height // 2}px;
    }}
    QSlider::handle:horizontal {{
        width: {t.slider_handle_size}px;
        height: {t.slider_handle_size}px;
        margin: {(t.slider_track_height - t.slider_handle_size) // 2}px 0;
        border: {t.slider_handle_border}px solid {t.accent_pressed};
        border-radius: {t.slider_handle_size // 2}px;
        background: {t.content_bg};
    }}
    QSlider::handle:horizontal:hover, QSlider::handle:horizontal:pressed {{
        border-color: {t.accent};
        background: {t.accent_soft};
    }}

    /* ---------- Lists / rows ---------- */
    QListWidget {{
        background: transparent;
        border: none;
        outline: none;
    }}
    QListWidget::item {{
        padding: {t.space_2}px {t.space_3}px;
        border-radius: {t.radius_sm}px;
        min-height: {t.row_height}px;
    }}
    QListWidget::item:hover {{
        background: rgba(0, 0, 0, 0.04);
    }}
    QListWidget::item:selected {{
        background: {t.accent_soft};
        color: {t.accent_pressed};
    }}

    /* Voice-profile rows use real child cards, so the native list item must
       stay transparent and leave all framing/selection paint to the card. */
    QListWidget#voiceProfileList {{
        selection-background-color: transparent;
        selection-color: {t.text_primary};
    }}
    QListWidget#voiceProfileList::item,
    QListWidget#voiceProfileList::item:hover,
    QListWidget#voiceProfileList::item:selected {{
        background: transparent;
        border: none;
        padding: 0;
        min-height: 0;
    }}
    QFrame#voiceProfileRow {{
        background: {t.content_bg};
        border: 1px solid {t.border_strong};
        border-radius: {t.radius_sm}px;
    }}
    QFrame#voiceProfileRow[selected="true"] {{
        background: {t.accent_soft};
        border: 1px solid {t.accent};
    }}
    QLabel#voiceProfileRowName {{
        background: transparent;
        border: none;
        font-weight: 500;
    }}
    QPushButton#previewVoiceProfileButton {{
        min-height: 32px;
        max-height: 32px;
        padding: 0 {t.space_3}px;
    }}
    QToolButton#voiceProfileMenuButton {{
        min-width: 34px;
        max-width: 34px;
        min-height: 34px;
        max-height: 34px;
        padding: 0;
        background: transparent;
        border: 1px solid transparent;
        border-radius: {t.radius_sm}px;
        font-size: 18px;
        font-weight: 600;
    }}
    QToolButton#voiceProfileMenuButton:hover {{
        background: rgba(0, 0, 0, 0.04);
        border-color: {t.border};
    }}
    QToolButton#voiceProfileMenuButton:focus {{
        border-color: {t.focus_ring};
    }}
    QToolButton#voiceProfileMenuButton::menu-indicator {{
        image: none;
        width: 0;
    }}

    /* ---------- Scrollbars: thin, unobtrusive ---------- */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(0, 0, 0, 0.18);
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: rgba(0, 0, 0, 0.32);
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}

    /* ---------- Menus / popovers (elevated, allowed a shadow) ---------- */
    QMenu {{
        background: {t.overlay_bg};
        border: 1px solid {t.border};
        border-radius: {t.radius_md}px;
        padding: {t.space_1}px;
    }}
    QMenu::item {{
        padding: {t.space_2}px {t.space_3}px;
        border-radius: {t.radius_sm}px;
    }}
    QMenu::item:selected {{
        background: {t.accent_soft};
        color: {t.accent_pressed};
    }}

    QToolTip {{
        background: {t.text_primary};
        color: {t.window_bg};
        border: none;
        border-radius: {t.radius_sm}px;
        padding: {t.space_1}px {t.space_2}px;
    }}
    """
