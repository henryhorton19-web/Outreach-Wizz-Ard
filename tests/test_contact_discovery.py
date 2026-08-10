"""Contact discovery must search for the person before guessing their address.

Failure case: TransactionLink / Mateusz Pniewski returned no contact, while a
single search found mpniewski@transactionlink.io as the first result.

Three defects, each sufficient on its own:
  1. no dedicated contact search -- it competed for a 4-search budget under a
     prompt telling the model "fewer is better, stop as soon as you have a contact"
  2. the pattern generator emitted only {first}@ and {first}.{last}@, so
     {first_initial}{last} -- the correct answer here -- was unreachable
  3. the guess was blind: the app never established what pattern the DOMAIN
     actually uses before guessing from the name
"""
import pathlib

import pytest

import app.research as research


def test_a_dedicated_contact_resolver_exists():
    """Mirrors resolve_company_domain, which already gets its own call and budget."""
    assert hasattr(research, "resolve_contact_email"), \
        "contact discovery still has no dedicated search step"


def test_pattern_generator_covers_first_initial_last():
    """The exact miss: mpniewski@ for Mateusz Pniewski."""
    cands = research.email_candidates("Mateusz Pniewski", "transactionlink.io")
    assert "mpniewski@transactionlink.io" in cands, \
        f"{{f}}{{last}} pattern missing; got {cands}"


def test_pattern_generator_covers_the_common_formats():
    cands = set(research.email_candidates("Mateusz Pniewski", "transactionlink.io"))
    for expected in ("mateusz@transactionlink.io",
                     "mateusz.pniewski@transactionlink.io",
                     "mpniewski@transactionlink.io",
                     "mateuszpniewski@transactionlink.io",
                     "m.pniewski@transactionlink.io",
                     "pniewski@transactionlink.io"):
        assert expected in cands, f"missing common format: {expected}"


def test_an_observed_address_pins_the_pattern():
    """Evidence beats guessing: given a real address at the domain, the format is
    known and must be applied rather than assumed."""
    pattern = research.infer_pattern("jkowalski@transactionlink.io", "Jan Kowalski")
    assert pattern == "{f}{last}", f"expected {{f}}{{last}}, got {pattern}"
    applied = research.apply_pattern(pattern, "Mateusz Pniewski", "transactionlink.io")
    assert applied == "mpniewski@transactionlink.io"


def test_candidates_are_ordered_most_likely_first():
    cands = research.email_candidates("Jane Doe", "example.com")
    assert cands[0] == "jane.doe@example.com"
    assert cands[1] == "jane@example.com", f"firstname@domain must be the primary pattern fallback; got {cands}"
    assert len(cands) >= 5


def test_the_prompt_no_longer_tells_the_model_to_stop_early_on_contact():
    src = pathlib.Path(__file__).parent.parent / "app" / "research.py"
    text = src.read_text(encoding="utf-8")
    assert "fewer is better" not in text, \
        "the ECONOMY directive still pushes the model to stop before finding a real contact"
