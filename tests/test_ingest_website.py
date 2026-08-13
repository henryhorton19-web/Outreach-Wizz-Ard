"""Column 2 of an uploaded sheet is the website, and it must survive all the way to research.

research._identity_anchor only anchors profiling to a domain when CompanyState.website is set;
without it the model is told to work out which company this is, and it picks the better-known one.
Two companies called Elix is the failure this prevents.
"""
import io

import pytest

from app import ingest, store


def _csv(text: str) -> bytes:
    return text.encode("utf-8")


def test_csv_second_column_is_read_as_website():
    rows = ingest.parse_csv_bytes(_csv("Elix AI,https://elix.ai\nTopograph,topograph.com\n"))
    assert [r["name"] for r in rows] == ["Elix AI", "Topograph"]
    assert rows[0]["website"] == "https://elix.ai"
    assert rows[1]["website"] == "topograph.com"


def test_csv_header_row_is_skipped_on_either_column():
    rows = ingest.parse_csv_bytes(_csv("Company,Website\nElix AI,https://elix.ai\n"))
    assert len(rows) == 1
    assert rows[0]["name"] == "Elix AI"


def test_csv_without_a_second_column_still_works():
    rows = ingest.parse_csv_bytes(_csv("Elix AI\nTopograph\n"))
    assert len(rows) == 2
    assert "website" not in rows[0]


def test_non_url_second_column_is_ignored_not_passed_to_research():
    rows = ingest.parse_csv_bytes(_csv("Elix AI,follow up next week\n"))
    assert rows[0]["name"] == "Elix AI"
    assert "website" not in rows[0], "a non-URL column 2 must not reach research as a website"


def test_pasted_text_website_reaches_the_queue_record(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "QUEUE_FILE", tmp_path / "queue.json")
    monkeypatch.setattr(store, "LISTS_FILE", tmp_path / "lists.json")
    store.upsert_queue("elix_ai", "Elix AI", None, None, list_id="default",
                       website="https://elix.ai")
    rec = [r for r in store.load_queue(list_id="default") if r["slug"] == "elix_ai"][0]
    assert rec["website"] == "https://elix.ai"


def test_clean_website_normalises_and_rejects():
    assert ingest._clean_website("  https://Elix.AI/about ") == "https://elix.ai/about"
    assert ingest._clean_website("www.elix.ai") == "www.elix.ai"
    assert ingest._clean_website("elix.ai") == "elix.ai"
    assert ingest._clean_website("call them Monday") == ""
    assert ingest._clean_website("") == ""
    assert ingest._clean_website(None) == ""
