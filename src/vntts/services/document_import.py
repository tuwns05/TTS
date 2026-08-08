"""Extract synthesis-ready plain text from supported document formats."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

from vntts.utils.exceptions import DocumentImportError

SUPPORTED_DOCUMENT_EXTENSIONS = (".txt", ".srt", ".docx", ".pdf")


@dataclass(frozen=True, slots=True)
class ImportedDocument:
    """Plain text extracted from one user-selected document."""

    source_path: Path
    text: str

    @property
    def display_name(self) -> str:
        """Return a concise source name suitable for the status bar."""

        return self.source_path.name


class DocumentTextImporter:
    """Convert TXT, SRT, DOCX and text-based PDF files to plain text."""

    def import_file(self, source_path: str | Path) -> ImportedDocument:
        """Read *source_path* and return normalized, synthesis-ready text."""

        path = Path(source_path)
        extension = path.suffix.lower()
        if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
            supported = ", ".join(SUPPORTED_DOCUMENT_EXTENSIONS)
            raise DocumentImportError(
                f"Định dạng '{extension or 'không xác định'}' chưa được hỗ trợ. "
                f"Hãy chọn một trong các định dạng: {supported}."
            )
        if not path.is_file():
            raise DocumentImportError(f"Không tìm thấy tệp '{path.name}'.")

        try:
            if extension == ".txt":
                text = self._read_text_file(path)
            elif extension == ".srt":
                text = self._extract_srt(self._read_text_file(path))
            elif extension == ".docx":
                text = self._extract_docx(path)
            else:
                text = self._extract_pdf(path)
        except DocumentImportError:
            raise
        except PermissionError as exc:
            raise DocumentImportError(
                f"Không có quyền đọc tệp '{path.name}'. Hãy đóng tệp nếu đang được ứng dụng khác sử dụng."
            ) from exc
        except OSError as exc:
            raise DocumentImportError(f"Không thể đọc tệp '{path.name}'.") from exc
        except Exception as exc:
            raise DocumentImportError(
                f"Không thể trích xuất nội dung từ tệp '{path.name}'. Tệp có thể bị hỏng."
            ) from exc

        normalized = self._normalize_text(text)
        if not normalized:
            detail = (
                " PDF có thể chỉ chứa ảnh; hãy dùng PDF có lớp văn bản hoặc OCR trước."
                if extension == ".pdf"
                else ""
            )
            raise DocumentImportError(f"Tệp '{path.name}' không có nội dung văn bản.{detail}")
        return ImportedDocument(source_path=path, text=normalized)

    @staticmethod
    def _read_text_file(path: Path) -> str:
        data = path.read_bytes()
        if data.startswith((b"\xff\xfe", b"\xfe\xff")):
            return data.decode("utf-16")
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                return data.decode("cp1258")
            except UnicodeDecodeError as exc:
                raise DocumentImportError(
                    f"Không nhận diện được bảng mã của tệp '{path.name}'. Hãy lưu tệp dưới dạng UTF-8."
                ) from exc

    @staticmethod
    def _extract_srt(source: str) -> str:
        normalized = source.replace("\r\n", "\n").replace("\r", "\n")
        captions: list[str] = []
        for block in re.split(r"\n\s*\n", normalized):
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if lines and lines[0].isdigit():
                lines.pop(0)
            if lines and "-->" in lines[0]:
                lines.pop(0)
            if not lines:
                continue
            caption = " ".join(lines)
            caption = re.sub(r"<[^>]+>", "", caption)
            caption = re.sub(r"\{\\[^}]+}", "", caption)
            caption = html.unescape(caption).strip()
            if caption:
                captions.append(caption)
        return "\n".join(captions)

    @staticmethod
    def _extract_docx(path: Path) -> str:
        try:
            from docx import Document
            from docx.table import Table
        except ImportError as exc:
            raise DocumentImportError(
                "Thiếu thư viện đọc DOCX. Hãy chạy lại 'py -3.11 -m pip install -e .'."
            ) from exc

        document = Document(path)
        blocks: list[str] = []
        for item in document.iter_inner_content():
            if isinstance(item, Table):
                for row in item.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if cells:
                        blocks.append("\t".join(cells))
            else:
                paragraph = item.text.strip()
                if paragraph:
                    blocks.append(paragraph)
        return "\n".join(blocks)

    @staticmethod
    def _extract_pdf(path: Path) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise DocumentImportError(
                "Thiếu thư viện đọc PDF. Hãy chạy lại 'py -3.11 -m pip install -e .'."
            ) from exc

        reader = PdfReader(path)
        if reader.is_encrypted:
            try:
                unlocked = reader.decrypt("")
            except Exception as exc:
                raise DocumentImportError(
                    f"PDF '{path.name}' đang được bảo vệ bằng mật khẩu."
                ) from exc
            if not unlocked:
                raise DocumentImportError(
                    f"PDF '{path.name}' đang được bảo vệ bằng mật khẩu."
                )
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
        return "\n\n".join(page for page in pages if page)

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.replace("\x00", "")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.rstrip() for line in text.splitlines()]
        normalized = "\n".join(lines).strip()
        return re.sub(r"\n{3,}", "\n\n", normalized)
