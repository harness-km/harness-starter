"""Week 0 tests: the course tools install, the dataset generates, and the fake model answers."""
import json
import sqlite3

import course_tools as ct
from course_tools.data.generate import generate
from course_tools.fake import FakeAnthropic


def test_dataset(tmp_path):
    out = generate(tmp_path, quiet=True)
    con = sqlite3.connect(out / "distributor.db")
    assert con.execute("select count(*) from suppliers").fetchone()[0] == 14
    assert len(list((out / "invoices").glob("*.pdf"))) == 40
    gt = json.loads((out / "ground_truth.json").read_text())["invoices"]
    inv_a = next(r for r in gt if r["id"] == "INV-A")["invoice"]
    assert inv_a["currency"] == "USD" and inv_a["total"] == 3360.0
    assert {r["currency"] for r in gt} == {"USD", "INR", "EUR", "CAD"}


def test_fake_model_answers():
    r = FakeAnthropic().messages.create(model=ct.MODELS["haiku"], max_tokens=50,
                                        messages=[{"role": "user", "content": "Say hello"}])
    assert r.stop_reason == "end_turn" and r.content[0].text


def test_prices_cover_models():
    assert set(ct.MODELS.values()) <= set(ct.PRICES_PER_MTOK)
