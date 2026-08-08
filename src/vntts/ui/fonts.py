"""Nạp font cục bộ lúc khởi động app.

Bản mockup HTML dùng Google Fonts qua CDN (<link href="fonts.googleapis.com...">)
— cách đó KHÔNG dùng được cho app thật vì vi phạm yêu cầu offline (NFR-01).
File font .ttf phải được tải sẵn và đặt trong ui/resources/fonts/ trước khi
build, không tải lúc chạy.

Cần chuẩn bị 3 bộ font (tải thủ công từ Google Fonts, đóng gói kèm installer):
  - Fraunces   (variable font, cần ít nhất 1-2 weight cho tiêu đề)
  - Inter      (400/500/600/700)
  - IBM Plex Mono (400/500)
Cả 3 đều có hỗ trợ tiếng Việt trong bộ glyph.
"""

from pathlib import Path

from loguru import logger
from PySide6.QtGui import QFontDatabase

FONT_DIR = Path(__file__).parent / "resources" / "fonts"


def load_app_fonts() -> list[str]:
    """Đăng ký toàn bộ file .ttf/.otf trong resources/fonts với Qt.

    Gọi hàm này một lần, sớm nhất có thể trong main.py — trước khi tạo
    QApplication các widget dùng font Fraunces/IBM Plex Mono, nếu không
    Qt sẽ fallback về font hệ thống mà không báo lỗi, rất khó nhận ra.
    """
    if not FONT_DIR.exists():
        logger.debug("Không tìm thấy thư mục font cục bộ; dùng font hệ thống.")
        return []
    loaded_families: list[str] = []
    for font_file in list(FONT_DIR.glob("*.ttf")) + list(FONT_DIR.glob("*.otf")):
        font_id = QFontDatabase.addApplicationFont(str(font_file))
        if font_id == -1:
            logger.warning("Không nạp được font cục bộ: {}", font_file.name)
            continue
        loaded_families.extend(QFontDatabase.applicationFontFamilies(font_id))
    return loaded_families
