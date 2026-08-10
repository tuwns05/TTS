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
"""

from dataclasses import dataclass
import platform

# --- Qt binding -------------------------------------------------------
# Default: PySide6. To use PyQt6 instead, comment the PySide6 line and
# uncomment the PyQt6 line — the rest of this file is binding-agnostic.
from PySide6.QtGui import QFont          # PyQt6: from PyQt6.QtGui import QFont


# --- Design tokens ------------------------------------------------------

@dataclass(frozen=True)
class Theme:
    # Surfaces (light mode, comfortable/consumer density)
    window_bg: str = "#F5F5F7"      # outermost window background
    panel_bg: str = "#FAFAFA"       # sidebar / toolbar background
    content_bg: str = "#FFFFFF"     # main content surface, cards
    border: str = "#E5E5EA"         # hairline border between surfaces
    overlay_bg: str = "#FFFFFF"     # menus, popovers, dialogs (elevated)

    # Text
    text_primary: str = "#1D1D1F"
    text_secondary: str = "#6E6E73"
    text_on_accent: str = "#FFFFFF"
    text_disabled: str = "#B9B9BE"

    # Accent — one color only. Used for primary action, selection,
    # active nav item. Never introduce a second saturated color.
    accent: str = "#0A84FF"
    accent_hover: str = "#3396FF"
    accent_pressed: str = "#0868CC"
    accent_soft: str = "rgba(10, 132, 255, 0.12)"    # selection / active-nav bg

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
    QLabel[role="caption"] {{
        font-size: {t.font_size_caption}px;
        color: {t.text_secondary};
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
    QGroupBox {{
        background: {t.content_bg};
        border: 1px solid {t.border};
        border-radius: {t.radius_md}px;
        margin-top: {t.space_3}px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: {t.space_3}px;
        padding: 0 {t.space_1}px;
        color: {t.text_primary};
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
        color: {t.accent_pressed};
        background: {t.accent_soft};
    }}
    QLabel#engineStatus[state="success"], QLabel#statusLabel[state="success"],
    QLabel#engineBadge[state="success"], QLabel#profileStatusLabel[state="success"] {{
        color: {t.accent_pressed};
        background: {t.accent_soft};
    }}

    QSlider::groove:horizontal {{
        height: 4px;
        border-radius: 2px;
        background: {t.border};
    }}
    QSlider::sub-page:horizontal {{
        background: {t.accent};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border: 2px solid {t.accent};
        border-radius: 8px;
        background: {t.content_bg};
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
