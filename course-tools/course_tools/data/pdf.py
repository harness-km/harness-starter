"""Render synthetic invoices as PDFs (digital, scanned, handwritten corrections), in any supported template."""
from __future__ import annotations

import io
import random
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .layout import document, money  # noqa: F401  (money is re-exported for older imports)

W, H = A4
ROWS_PER_PAGE = 20
COL_X = [40, 58, 262, 300, 340, 410, 515]


def _header(c: canvas.Canvas, doc: dict, page: int, pages: int) -> float:
    c.setFont("Helvetica-Bold", 15)
    c.drawString(40, H - 50, doc["supplier"])
    c.setFont("Helvetica", 9)
    c.drawString(40, H - 64, doc["supplier_line"])
    c.drawString(40, H - 76, doc["email"])
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(W - 40, H - 50, doc["title"])
    c.setFont("Helvetica", 9)
    c.drawRightString(W - 40, H - 64, f"Page {page} of {pages}")
    c.line(40, H - 86, W - 40, H - 86)
    y = H - 102
    for x, text in zip((40, 230, 400), doc["meta"]):
        c.drawString(x, y, text)
    y -= 16
    c.drawString(40, y, doc["bill_to"])
    y -= 12
    c.drawString(40, y, doc["buyer"])
    return y - 18


def _table_header(c: canvas.Canvas, y: float, doc: dict) -> float:
    c.setFont("Helvetica-Bold", 8.5)
    for x, label in zip(COL_X, doc["columns"]):
        c.drawString(x, y, label)
    c.line(40, y - 4, W - 40, y - 4)
    return y - 16


def _row(c: canvas.Canvas, y: float, cells: list[str], printed_qty=None) -> None:
    c.setFont("Helvetica", 8.5)
    c.drawString(40, y, cells[0])
    c.drawString(58, y, cells[1][:40])
    c.drawString(262, y, cells[2])
    c.drawRightString(328, y, str(printed_qty) if printed_qty is not None else cells[3])
    c.drawRightString(395, y, cells[4])
    c.drawRightString(500, y, cells[5])
    c.drawRightString(540, y, cells[6])


def _handwritten(c: canvas.Canvas, y: float, new_qty: int) -> None:
    c.setStrokeColorRGB(0.1, 0.2, 0.7)
    c.setLineWidth(1.2)
    c.line(308, y + 3, 330, y + 3)
    c.saveState()
    c.setFillColorRGB(0.1, 0.2, 0.7)
    c.translate(333, y + 1)
    c.rotate(-6)
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(0, 0, str(new_qty))
    c.setFont("Helvetica-Oblique", 7)
    c.drawString(16, -3, "RK")
    c.restoreState()
    c.setStrokeColorRGB(0, 0, 0)
    c.setFillColorRGB(0, 0, 0)
    c.setLineWidth(1)


def _totals(c: canvas.Canvas, y: float, doc: dict, footer: str | None) -> None:
    c.line(40, y + 8, W - 40, y + 8)
    c.setFont("Helvetica", 9)
    for label, val in doc["totals"]:
        c.drawString(300, y, label)
        c.drawRightString(540, y, val)
        y -= 13
    c.setFont("Helvetica-Bold", 10)
    c.drawString(300, y, doc["total"][0])
    c.drawRightString(540, y, doc["total"][1])
    y -= 28
    c.setFont("Helvetica", 9)
    c.drawString(40, y, "Bank details for payment:")
    c.drawString(40, y - 12, doc["bank"])
    y -= 40
    c.drawString(40, y, doc["terms"])
    c.drawRightString(W - 40, y, f"For {doc['supplier']}")
    c.drawRightString(W - 40, y - 30, "Authorised signatory")
    if footer:
        c.setFont("Helvetica", 7.5)
        c.drawString(40, 40, footer)


def render_digital(path: Path, inv: dict, sup: dict, entity: dict, label: str | None = None,
                   handwritten: dict | None = None, footer: str | None = None) -> int:
    """Draw the invoice. handwritten = {line_index: printed_qty}; returns page count."""
    doc = document(inv, sup, entity, label)
    rows = doc["rows"]
    pages = max(1, -(-len(rows) // ROWS_PER_PAGE))
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle(f"Invoice {inv['invoice_number']}")
    for p in range(pages):
        y = _header(c, doc, p + 1, pages)
        y = _table_header(c, y, doc)
        for j, cells in enumerate(rows[p * ROWS_PER_PAGE:(p + 1) * ROWS_PER_PAGE]):
            idx = p * ROWS_PER_PAGE + j
            printed = handwritten.get(idx) if handwritten else None
            _row(c, y, cells, printed_qty=printed)
            if printed is not None:
                _handwritten(c, y, inv["lines"][idx]["quantity"])
            y -= 14
        if p == pages - 1:
            _totals(c, y - 10, doc, footer)
        else:
            c.setFont("Helvetica-Oblique", 8.5)
            c.drawString(40, y - 10, "Continued on next page")
        c.showPage()
    c.save()
    return pages


def rasterise(path: Path, dpi: int, seed: int, blur: float = 0.4, noise: int = 12, angle: float = 0.8) -> None:
    """Turn a digital PDF into a 'scanned' image-only PDF (no text layer)."""
    import pymupdf as fitz
    from PIL import Image, ImageFilter

    rng = random.Random(seed)
    doc = fitz.open(str(path))
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
        img = img.rotate(angle * rng.choice([-1, 1]), expand=True, fillcolor=255)
        if dpi < 60:
            img = img.resize((img.width * 3, img.height * 3))
        img = img.filter(ImageFilter.GaussianBlur(blur))
        px = img.load()
        for _ in range(img.width * img.height // 40):
            x, y = rng.randrange(img.width), rng.randrange(img.height)
            px[x, y] = max(0, min(255, px[x, y] + rng.randint(-noise * 4, noise * 4)))
        images.append(img.convert("RGB"))
    doc.close()
    images[0].save(str(path), save_all=True, append_images=images[1:], resolution=dpi)
