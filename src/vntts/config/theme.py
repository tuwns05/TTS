"""Design tokens and the generated Qt stylesheet for the desktop UI."""

from PySide6.QtGui import QFontDatabase, QGuiApplication


class Color:
    """Graphite surfaces with amber and teal as the only accent colors."""

    INK = "#12151A"
    INK_SOFT = "#171B22"
    PANEL = "#1C212B"
    PANEL_RAISED = "#252B36"
    BORDER = "#2C3340"
    BORDER_SOFT = "#232936"

    BONE = "#ECE7DC"
    BONE_DIM = "#B9B4A8"
    SLATE = "#8891A0"
    SLATE_DIM = "#5B6270"

    AMBER = "#E3A857"
    AMBER_HOVER = "#EDB96F"
    AMBER_PRESSED = "#C98F42"
    AMBER_SOFT = "rgba(227, 168, 87, 36)"
    TEAL = "#5FC9C0"
    TEAL_SOFT = "rgba(95, 201, 192, 36)"
    DANGER = "#E17B6B"
    DANGER_SOFT = "rgba(225, 123, 107, 32)"


class Font:
    DISPLAY = "Fraunces"
    BODY = "Inter"
    MONO = "IBM Plex Mono"


class Radius:
    SM = 6
    MD = 10
    LG = 18


def _font_family(preferred: str, fallback: str) -> str:
    """Return a readable local fallback when bundled fonts are not installed."""

    if QGuiApplication.instance() is None:
        return fallback
    return preferred if preferred in QFontDatabase.families() else fallback


def build_stylesheet() -> str:
    """Build one stylesheet from the shared design tokens.

    Qt stylesheets do not support CSS custom properties. Generating the QSS here
    keeps color, typography and radius values in one source of truth.
    """

    body_font = _font_family(Font.BODY, "Segoe UI")
    display_font = _font_family(Font.DISPLAY, "Georgia")
    mono_font = _font_family(Font.MONO, "Consolas")

    return f"""
    * {{
        color: {Color.BONE};
        font-family: "{body_font}";
        font-size: 13px;
        font-weight: 400;
    }}

    QMainWindow#AppRoot,
    QWidget#appSurface,
    QScrollArea#contentScrollArea,
    QScrollArea#contentScrollArea > QWidget > QWidget {{
        background-color: {Color.INK};
        border: none;
    }}

    QScrollBar:vertical {{
        width: 9px;
        margin: 2px;
        background: {Color.INK};
    }}
    QScrollBar::handle:vertical {{
        min-height: 36px;
        border-radius: 4px;
        background: {Color.BORDER};
    }}
    QScrollBar::handle:vertical:hover {{ background: {Color.SLATE_DIM}; }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        height: 0;
        background: transparent;
    }}

    QLabel#eyebrow {{
        color: {Color.TEAL};
        font-family: "{mono_font}";
        font-size: 10px;
        font-weight: 600;
    }}
    QLabel#eyebrow {{
        color: {Color.TEAL};
        font-family: "{mono_font}";
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
    }}
    QLabel#appTitle {{
        color: {Color.BONE};
        font-family: "{display_font}";
        font-size: 28px;
        font-weight: 600;
    }}
    QLabel#appSubtitle,
    QLabel#helperText {{
        color: {Color.SLATE};
        font-size: 12px;
        line-height: 1.4;
    }}
    QLabel#sectionTitle {{
        color: {Color.BONE};
        font-family: "{display_font}";
        font-size: 17px;
        font-weight: 600;
    }}
    QLabel#fieldLabel {{
        color: {Color.BONE_DIM};
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#characterCount,
    QLabel#metricValue,
    QLabel#timeLabel {{
        color: {Color.SLATE};
        font-family: "{mono_font}";
        font-size: 11px;
        font-weight: 500;
    }}
    QLabel#engineBadge {{
        color: {Color.BONE};
        background-color: {Color.PANEL_RAISED};
        border: 1px solid {Color.BORDER};
        border-radius: {Radius.SM}px;
        padding: 8px 12px;
        font-size: 11px;
        font-weight: 600;
    }}
    QLabel#engineBadge[state="success"] {{
        color: {Color.TEAL};
        background-color: {Color.TEAL_SOFT};
        border-color: {Color.TEAL};
    }}

    QFrame#composerCard,
    QFrame#playerCard,
    QWidget#enginePanel,
    QWidget#settingsContainer,
    QGroupBox#voiceSettingsCard {{
        background-color: {Color.PANEL};
        border: 1px solid {Color.BORDER_SOFT};
        border-radius: {Radius.LG}px;
    }}
    QGroupBox#voiceSettingsCard {{
        margin-top: 16px;
        padding-top: 8px;
        color: {Color.BONE};
        font-family: "{display_font}";
        font-size: 17px;
        font-weight: 600;
    }}
    QGroupBox#voiceSettingsCard::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 16px;
        padding: 0 5px;
        color: {Color.BONE};
        background-color: {Color.PANEL};
    }}
    QFrame#sectionDivider {{
        max-height: 1px;
        border: none;
        background-color: {Color.BORDER_SOFT};
    }}

    QPlainTextEdit,
    QComboBox {{
        color: {Color.BONE};
        background-color: {Color.INK_SOFT};
        border: 1px solid {Color.BORDER};
        border-radius: {Radius.MD}px;
        padding: 9px 12px;
        selection-background-color: {Color.AMBER_SOFT};
        selection-color: {Color.BONE};
    }}
    QPlainTextEdit#textInput {{
        min-height: 320px;
        padding: 14px 14px;
        font-size: 14px;
        line-height: 1.5;
    }}
    QPlainTextEdit:hover,
    QComboBox:hover {{ border-color: {Color.SLATE_DIM}; }}
    QPlainTextEdit:focus,
    QComboBox:focus {{ border: 1px solid {Color.AMBER}; }}
    QPlainTextEdit:disabled,
    QComboBox:disabled {{
        color: {Color.SLATE_DIM};
        background-color: {Color.INK_SOFT};
        border-color: {Color.BORDER_SOFT};
    }}
    QComboBox::drop-down {{
        width: 34px;
        border: none;
    }}
    QComboBox QAbstractItemView {{
        color: {Color.BONE};
        background-color: {Color.PANEL_RAISED};
        border: 1px solid {Color.BORDER};
        selection-color: {Color.INK};
        selection-background-color: {Color.AMBER};
        outline: none;
        padding: 6px;
    }}

    QPushButton {{
        min-height: 42px;
        padding: 0 16px;
        color: {Color.BONE_DIM};
        background-color: transparent;
        border: 1px solid {Color.BORDER};
        border-radius: 9px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        color: {Color.BONE};
        background-color: {Color.PANEL_RAISED};
        border-color: {Color.SLATE_DIM};
    }}
    QPushButton:focus {{ border: 1px solid {Color.TEAL}; }}
    QPushButton:pressed {{ background-color: {Color.BORDER}; }}
    QPushButton:disabled {{
        color: {Color.SLATE_DIM};
        background-color: {Color.INK_SOFT};
        border-color: {Color.BORDER_SOFT};
    }}
    QPushButton#synthesizeButton {{
        min-height: 48px;
        color: {Color.INK};
        background-color: {Color.AMBER};
        border: 1px solid {Color.AMBER};
        font-size: 14px;
        font-weight: 700;
    }}
    QPushButton#synthesizeButton:hover {{
        color: {Color.INK};
        background-color: {Color.AMBER_HOVER};
        border-color: {Color.AMBER_HOVER};
    }}
    QPushButton#synthesizeButton:pressed {{ background-color: {Color.AMBER_PRESSED}; }}
    QPushButton#synthesizeButton:disabled {{
        color: {Color.SLATE_DIM};
        background-color: {Color.PANEL_RAISED};
        border-color: {Color.PANEL_RAISED};
    }}
    QPushButton#cancelButton {{
        color: {Color.DANGER};
        background-color: transparent;
        border-color: {Color.BORDER};
    }}
    QPushButton#cancelButton:hover {{
        color: {Color.DANGER};
        background-color: {Color.DANGER_SOFT};
        border-color: {Color.DANGER};
    }}

    QPushButton#playButton,
    QPushButton#pauseButton,
    QPushButton#stopButton {{
        min-width: 42px;
        max-width: 42px;
        min-height: 42px;
        max-height: 42px;
        padding: 0;
        border-radius: 21px;
        font-size: 15px;
    }}
    QPushButton#playButton {{
        min-width: 50px;
        max-width: 50px;
        min-height: 50px;
        max-height: 50px;
        border-radius: 25px;
        color: {Color.INK};
        background-color: {Color.AMBER};
        border-color: {Color.AMBER};
    }}
    QPushButton#playButton:hover {{ background-color: {Color.AMBER_HOVER}; }}
    QPushButton#playButton:disabled,
    QPushButton#pauseButton:disabled,
    QPushButton#stopButton:disabled {{
        color: {Color.SLATE_DIM};
        background-color: {Color.INK_SOFT};
        border-color: {Color.BORDER_SOFT};
    }}

    QLabel#engineStatus,
    QLabel#statusLabel {{
        border-radius: {Radius.SM}px;
        padding: 7px 10px;
        font-size: 11px;
        font-weight: 600;
    }}
    QLabel#engineStatus[state="neutral"],
    QLabel#statusLabel[state="neutral"] {{
        color: {Color.SLATE};
        background-color: {Color.INK_SOFT};
    }}
    QLabel#engineStatus[state="busy"],
    QLabel#statusLabel[state="busy"] {{
        color: {Color.AMBER};
        background-color: {Color.AMBER_SOFT};
    }}
    QLabel#engineStatus[state="success"],
    QLabel#statusLabel[state="success"] {{
        color: {Color.TEAL};
        background-color: {Color.TEAL_SOFT};
    }}
    QLabel#engineStatus[state="error"],
    QLabel#statusLabel[state="error"] {{
        color: {Color.DANGER};
        background-color: {Color.DANGER_SOFT};
    }}
    QLabel#recommendationLabel {{
        color: {Color.SLATE};
        background-color: {Color.INK_SOFT};
        border-radius: {Radius.MD}px;
        padding: 9px 10px;
        font-size: 11px;
    }}

    QSlider::groove:horizontal {{
        height: 4px;
        border-radius: 2px;
        background: {Color.BORDER};
    }}
    QSlider::sub-page:horizontal {{
        border-radius: 2px;
        background: {Color.TEAL};
    }}
    QSlider::add-page:horizontal {{
        border-radius: 2px;
        background: {Color.BORDER};
    }}
    QSlider::handle:horizontal {{
        width: 14px;
        height: 14px;
        margin: -6px 0;
        border: 2px solid {Color.TEAL};
        border-radius: 8px;
        background: {Color.BONE};
    }}
    QSlider::handle:horizontal:hover {{ border-color: {Color.BONE}; }}
    QSlider::handle:horizontal:disabled {{
        border-color: {Color.SLATE_DIM};
        background: {Color.PANEL_RAISED};
    }}
    QSlider::sub-page:horizontal:disabled {{ background: {Color.SLATE_DIM}; }}

    QWidget#audioTimeline {{
        background-color: transparent;
        border: none;
    }}
    """
