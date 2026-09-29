"""Week 0: setup."""
import os
import sqlite3
from pathlib import Path

from ..config import MODELS, data_dir, fake_mode, in_colab
from . import expect

USES_MODEL = False  # this check talks to the real Claude unless the whole notebook runs offline
SUMMARY = "Secrets OK · Claude reachable · Drive mounted · Dataset OK"


def secrets_ok(ns):
    """Secrets OK: the API key is loaded from secrets, not typed into the notebook"""
    if fake_mode():
        return
    expect(bool(os.environ.get("ANTHROPIC_API_KEY")),
           "No ANTHROPIC_API_KEY. Add it in Colab Secrets (key icon) and turn on Notebook access, then re-run the "
           "bootstrap cell.")
    key = os.environ["ANTHROPIC_API_KEY"]
    for name, value in ns.items():
        if isinstance(value, str) and value == key and not name.startswith("_"):
            raise AssertionError(f"The key is stored in the notebook variable `{name}`. Delete that cell and use "
                                 "Secrets instead.")


def claude_reachable(ns):
    """Claude reachable: a one-line call to Haiku succeeds"""
    import anthropic
    client = anthropic.Anthropic()
    r = client.messages.create(model=MODELS["haiku"], max_tokens=20,
                               messages=[{"role": "user", "content": "Reply with the word ready."}])
    expect(r.content and r.content[0].text.strip() != "", "Claude replied with no text.")


def drive_mounted(ns):
    """Drive mounted: the dataset is saved to Google Drive (Colab only)"""
    if not in_colab():
        return
    expect(Path("/content/drive/MyDrive").exists(), "Google Drive is not mounted. Run the Drive cell and approve it.")


def dataset_ok(ns):
    """Dataset OK: distributor.db and 40 invoice PDFs are present"""
    d = data_dir()
    db = d / "distributor.db"
    expect(db.exists(), f"No database at {db}. Run the bootstrap cell.")
    con = sqlite3.connect(db)
    try:
        n_sup = con.execute("select count(*) from suppliers").fetchone()[0]
        n_po = con.execute("select count(*) from purchase_orders").fetchone()[0]
    finally:
        con.close()
    expect(n_sup == 8 and n_po >= 60, f"Unexpected dataset contents ({n_sup} suppliers, {n_po} POs).")
    pdfs = list((d / "invoices").glob("*.pdf"))
    expect(len(pdfs) == 40, f"Expected 40 invoice PDFs, found {len(pdfs)}.")


CHECKS = [secrets_ok, claude_reachable, drive_mounted, dataset_ok]
