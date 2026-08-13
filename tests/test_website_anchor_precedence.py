"""The operator-supplied website must beat the machine's own resolved domain, and must be able to
invalidate a cache built around the wrong company.

Regression: pasting https://www.massive-dynamic.ai/ on an already-drafted target left the draft
addressed at massiveds.com, because (a) cs.recipient_domain -- written FROM research output -- was
read in preference to cs.website, and (b) draft_one only researches when the cache is None.
"""
import pytest

from app import pipeline, store, settings as S
from app.models import CompanyState, State


@pytest.fixture(autouse=True)
def iso(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "DATA_DIR", tmp_path)
    monkeypatch.setattr(store, "DRAFTS_FILE", tmp_path / "drafts.json")
    monkeypatch.setattr(S, "SETTINGS_FILE", tmp_path / "settings.json")
    yield


# ---- Defect 1: precedence --------------------------------------------------

def test_operator_website_outranks_resolved_domain():
    cs = CompanyState(slug="md", name="Massive Dynamic",
                      website="https://www.massive-dynamic.ai/",
                      recipient_domain="massiveds.com")
    assert pipeline.anchor_site(cs) == "https://www.massive-dynamic.ai/"


def test_resolved_domain_is_used_when_no_website_was_given():
    cs = CompanteState = CompanyState(slug="md", name="Massive Dynamic",
                                      recipient_domain="massiveds.com")
    assert pipeline.anchor_site(cs) == "massiveds.com"


def test_anchor_site_is_empty_when_neither_is_set():
    assert pipeline.anchor_site(CompanyState(slug="md", name="Massive Dynamic")) == ""


# ---- Defect 2: cache invalidation -----------------------------------------

def _cache(domain):
    return {"company": {"name": "Massive Data Systems", "website": f"https://{domain}",
                        "resolved_domain": domain, "what_they_do": "data"},
            "contact": {"name": "A B", "email": f"a.b@{domain}"},
            "proof_points": [{"fact": "something"}]}


def test_cache_about_a_different_domain_is_stale():
    cs = CompanyState(slug="md", name="Massive Dynamic",
                      website="https://www.massive-dynamic.ai/")
    assert pipeline.cache_contradicts_website(cs, _cache("massiveds.com")) is True


def test_cache_matching_the_website_is_kept():
    cs = CompanyState(slug="md", name="Massive Dynamic",
                      website="https://www.massive-dynamic.ai/")
    assert pipeline.cache_contradicts_website(cs, _cache("massive-dynamic.ai")) is False


def test_www_and_scheme_differences_are_not_a_contradiction():
    cs = CompanyState(slug="md", name="Massive Dynamic", website="massive-dynamic.ai")
    assert pipeline.cache_contradicts_website(cs, _cache("www.massive-dynamic.ai")) is False


def test_no_website_means_no_contradiction():
    cs = CompanyState(slug="md", name="Massive Dynamic")
    assert pipeline.cache_contradicts_website(cs, _cache("massiveds.com")) is False


def test_never_raises_on_garbage():
    cs = CompanyState(slug="md", name="X", website="massive-dynamic.ai")
    for bad in (None, {}, {"company": None}, {"company": {"resolved_domain": None}}):
        assert pipeline.cache_contradicts_website(cs, bad) in (True, False)


# ---- Defect 4: the address must agree with the anchor ---------------------

def test_email_on_a_foreign_domain_is_dropped():
    cache = _cache("massiveds.com")
    out = pipeline.strip_foreign_contact_email(cache, "massive-dynamic.ai")
    assert not (out.get("contact") or {}).get("email")
    assert (out.get("contact") or {}).get("email_method") == "dropped_domain_mismatch"


def test_email_on_the_anchor_domain_is_kept():
    cache = _cache("massive-dynamic.ai")
    out = pipeline.strip_foreign_contact_email(cache, "massive-dynamic.ai")
    assert (out.get("contact") or {}).get("email") == "a.b@massive-dynamic.ai"


def test_subdomain_of_the_anchor_is_kept():
    cache = _cache("mail.massive-dynamic.ai")
    out = pipeline.strip_foreign_contact_email(cache, "massive-dynamic.ai")
    assert (out.get("contact") or {}).get("email")


def test_no_anchor_means_no_stripping():
    cache = _cache("massiveds.com")
    out = pipeline.strip_foreign_contact_email(cache, "")
    assert (out.get("contact") or {}).get("email") == "a.b@massiveds.com"
