"""Извлечение текста из PDF / DOCX / XLSX / изображений."""

from __future__ import annotations

from pathlib import Path


class ExtractionResult:
    def __init__(self, text: str, method: str, error: str = "") -> None:
        self.text = text
        self.method = method
        self.error = error

    def __repr__(self) -> str:
        return f"ExtractionResult(method={self.method!r}, len={len(self.text)}, error={self.error!r})"


def tesseract_available() -> bool:
    try:
        import pytesseract  # noqa: PLC0415
        pytesseract.get_tesseract_version()
        return True
    except Exception:  # noqa: BLE001
        return False


def extract_text(path: Path) -> ExtractionResult:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix == ".docx":
        return _extract_docx(path)
    if suffix in (".xlsx", ".xls"):
        return _extract_xlsx(path)
    if suffix in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"):
        return _extract_image(path)
    if suffix == ".txt":
        try:
            return ExtractionResult(path.read_text(encoding="utf-8"), "txt")
        except UnicodeDecodeError:
            return ExtractionResult(path.read_text(encoding="cp1251"), "txt")
    return ExtractionResult("", "unsupported", f"Неподдерживаемый формат: {suffix}")


def _extract_pdf(path: Path) -> ExtractionResult:
    try:
        import fitz  # PyMuPDF  # noqa: PLC0415
    except ImportError:
        return ExtractionResult("", "pdf", "PyMuPDF не установлен")

    try:
        doc = fitz.open(str(path))
    except Exception as exc:  # noqa: BLE001
        return ExtractionResult("", "pdf", f"Не удалось открыть PDF: {exc}")

    parts = []
    for page in doc:
        parts.append(page.get_text())
    text = "\n".join(parts).strip()
    if text:
        return ExtractionResult(text, "pdf_text")

    # Текстового слоя нет — пробуем OCR
    if not tesseract_available():
        return ExtractionResult(
            "",
            "pdf_no_text_layer",
            "PDF без текстового слоя. Установите Tesseract: brew install tesseract tesseract-lang",
        )
    try:
        import io

        import pytesseract
        from PIL import Image

        ocr_parts = []
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            ocr_parts.append(pytesseract.image_to_string(img, lang="rus+eng"))
        return ExtractionResult("\n".join(ocr_parts).strip(), "pdf_ocr")
    except Exception as exc:  # noqa: BLE001
        return ExtractionResult("", "pdf_ocr", f"OCR ошибка: {exc}")


def _extract_docx(path: Path) -> ExtractionResult:
    try:
        from docx import Document  # noqa: PLC0415
    except ImportError:
        return ExtractionResult("", "docx", "python-docx не установлен")
    try:
        doc = Document(str(path))
    except Exception as exc:  # noqa: BLE001
        return ExtractionResult("", "docx", f"Не удалось открыть DOCX: {exc}")

    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return ExtractionResult("\n".join(parts).strip(), "docx")


def _extract_xlsx(path: Path) -> ExtractionResult:
    try:
        from openpyxl import load_workbook  # noqa: PLC0415
    except ImportError:
        return ExtractionResult("", "xlsx", "openpyxl не установлен")
    try:
        wb = load_workbook(str(path), data_only=True)
    except Exception as exc:  # noqa: BLE001
        return ExtractionResult("", "xlsx", f"Не удалось открыть XLSX: {exc}")
    parts = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            for v in row:
                if v is not None:
                    parts.append(str(v))
    return ExtractionResult("\n".join(parts).strip(), "xlsx")


def _extract_image(path: Path) -> ExtractionResult:
    if not tesseract_available():
        return ExtractionResult(
            "", "image", "OCR недоступен. Установите Tesseract: brew install tesseract tesseract-lang"
        )
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(str(path))
        text = pytesseract.image_to_string(img, lang="rus+eng")
        return ExtractionResult(text.strip(), "image_ocr")
    except Exception as exc:  # noqa: BLE001
        return ExtractionResult("", "image_ocr", f"OCR ошибка: {exc}")
