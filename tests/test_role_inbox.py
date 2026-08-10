"""A shared role inbox is not a person's address.

Real run: Stych returned contact.name "Stanislas Llurens" with email
nous-contacter@stych.fr, marked email_confidence "high" and contact_verified
true. "nous-contacter" is literally "contact us". Worse, research.py generates
contact@ and hello@ as fallbacks, so the system can invent a role address and
then mark it verified.
"""
import app.research as research


def test_common_role_locals_are_detected():
    for addr in ("contact@x.com", "hello@x.com", "info@x.com", "nous-contacter@stych.fr",
                 "support@x.com", "team@x.com", "sales@x.com", "admin@x.com"):
        assert research.is_role_inbox(addr), f"{addr} was not detected as a role inbox"


def test_personal_addresses_are_not_flagged():
    for addr in ("nicolas@swan.io", "frederic.plais@upsun.com", "mpniewski@transactionlink.io",
                 "s.llurens@stych.fr"):
        assert not research.is_role_inbox(addr), f"{addr} was wrongly flagged as a role inbox"


def test_a_role_inbox_cannot_be_high_confidence_for_a_named_person():
    cache = {"contact": {"name": "Stanislas Llurens", "email": "nous-contacter@stych.fr",
                         "email_confidence": "high", "contact_verified": True}}
    out = research.downgrade_role_inbox(cache)
    c = out["contact"]
    assert c["email_confidence"] != "high"
    assert c["contact_verified"] is False


def test_a_role_inbox_with_no_named_person_is_left_alone():
    """Writing to a company inbox is legitimate when you have no name."""
    cache = {"contact": {"name": "", "email": "contact@x.com",
                         "email_confidence": "medium", "contact_verified": False}}
    assert research.downgrade_role_inbox(cache)["contact"]["email_confidence"] == "medium"
