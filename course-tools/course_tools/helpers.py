"""Small display and error helpers used in the labs."""
from __future__ import annotations

from pathlib import Path


def show_pdf(path, page: int = 0, dpi: int = 80):
    """Display one page of a PDF inline in the notebook."""
    import pymupdf
    from IPython.display import Image, display
    doc = pymupdf.open(str(path))
    try:
        display(Image(data=doc[page].get_pixmap(dpi=dpi).tobytes("png")))
    finally:
        doc.close()


def validation_summary(err: Exception) -> list[tuple[str, str]]:
    """[(field, message)] from a Pydantic ValidationError, even when a framework wrapped it."""
    from pydantic import ValidationError
    seen = set()
    e = err
    while e is not None and id(e) not in seen:
        seen.add(id(e))
        if isinstance(e, ValidationError):
            out = []
            for item in e.errors():
                loc = ".".join(str(x) for x in item.get("loc", ())) or "(invoice)"
                out.append((loc, item.get("msg", "")))
            return out
        e = e.__cause__ or e.__context__
    return [("(unknown)", str(err)[:200])]


def invoice_path(env, invoice_id: str) -> Path:
    return Path(env.invoices) / f"{invoice_id}.pdf"
