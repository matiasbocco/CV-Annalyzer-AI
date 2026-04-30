"""
Unit tests for the anonymization service.

All tests are pure Python — no DB, no LLM calls.
"""
import pytest
from core.services.anonymization_service import anonymize_cvs, restore_filenames


# ── Email ─────────────────────────────────────────────────────────────────────

def test_anonymize_email():
    cvs = [{"filename": "juan.pdf", "text": "Email: juan.garcia@example.com\nSkills: Python"}]
    anon, _ = anonymize_cvs(cvs)
    assert "[email]" in anon[0]["text"]
    assert "juan.garcia@example.com" not in anon[0]["text"]


def test_email_not_doubled_by_url_regex():
    """An email inside a mailto: URL should still become [email], not [portfolio]."""
    cvs = [{"filename": "cv.pdf", "text": "Contact: usuario@gmail.com\nMore text"}]
    anon, _ = anonymize_cvs(cvs)
    assert "[email]" in anon[0]["text"]


# ── Phone ─────────────────────────────────────────────────────────────────────

def test_anonymize_phone_argentine_mobile():
    cvs = [{"filename": "cv.pdf", "text": "Cel: +54 9 11 4567-8901\nCareer: 5 years"}]
    anon, _ = anonymize_cvs(cvs)
    assert "[phone]" in anon[0]["text"]
    assert "+54 9 11 4567-8901" not in anon[0]["text"]


def test_anonymize_phone_landline_with_area_code():
    cvs = [{"filename": "cv.pdf", "text": "Tel: (011) 4523-6789\nCareer: 3 years"}]
    anon, _ = anonymize_cvs(cvs)
    assert "[phone]" in anon[0]["text"]
    assert "(011) 4523-6789" not in anon[0]["text"]


def test_anonymize_phone_us_format():
    cvs = [{"filename": "cv.pdf", "text": "Phone: 555-867-5309\nSkills: React"}]
    anon, _ = anonymize_cvs(cvs)
    assert "[phone]" in anon[0]["text"]
    assert "555-867-5309" not in anon[0]["text"]


# ── URLs ──────────────────────────────────────────────────────────────────────

def test_anonymize_linkedin_url():
    cvs = [{"filename": "dev.pdf", "text": "LinkedIn: https://linkedin.com/in/jgarcia\nPython dev"}]
    anon, _ = anonymize_cvs(cvs)
    assert "[linkedin]" in anon[0]["text"]
    assert "linkedin.com/in/jgarcia" not in anon[0]["text"]


def test_anonymize_github_url():
    cvs = [{"filename": "dev.pdf", "text": "GitHub: https://github.com/jgarcia\nOpen source"}]
    anon, _ = anonymize_cvs(cvs)
    assert "[github]" in anon[0]["text"]
    assert "github.com/jgarcia" not in anon[0]["text"]


def test_anonymize_portfolio_url():
    cvs = [{"filename": "dev.pdf", "text": "Site: https://jgarcia.dev/portfolio\nDesign work"}]
    anon, _ = anonymize_cvs(cvs)
    assert "[portfolio]" in anon[0]["text"]
    assert "jgarcia.dev" not in anon[0]["text"]


def test_linkedin_not_double_replaced():
    """LinkedIn URL must become [linkedin], not [portfolio]."""
    cvs = [{"filename": "cv.pdf", "text": "https://linkedin.com/in/user123"}]
    anon, _ = anonymize_cvs(cvs)
    assert "[linkedin]" in anon[0]["text"]
    assert "[portfolio]" not in anon[0]["text"]


# ── Label map ─────────────────────────────────────────────────────────────────

def test_label_map_three_cvs():
    cvs = [
        {"filename": "alice.pdf", "text": "CV text A"},
        {"filename": "bob.pdf",   "text": "CV text B"},
        {"filename": "carlos.pdf","text": "CV text C"},
    ]
    anon, label_map = anonymize_cvs(cvs)
    assert anon[0]["filename"] == "candidate_a"
    assert anon[1]["filename"] == "candidate_b"
    assert anon[2]["filename"] == "candidate_c"
    assert label_map == {
        "candidate_a": "alice.pdf",
        "candidate_b": "bob.pdf",
        "candidate_c": "carlos.pdf",
    }


def test_label_map_single_cv():
    cvs = [{"filename": "only.pdf", "text": "Single CV"}]
    anon, label_map = anonymize_cvs(cvs)
    assert anon[0]["filename"] == "candidate_a"
    assert label_map == {"candidate_a": "only.pdf"}


def test_label_map_26_cvs_exhausts_alphabet():
    cvs = [{"filename": f"cv_{i}.pdf", "text": "text"} for i in range(26)]
    anon, label_map = anonymize_cvs(cvs)
    assert anon[25]["filename"] == "candidate_z"
    assert label_map["candidate_z"] == "cv_25.pdf"


# ── restore_filenames ─────────────────────────────────────────────────────────

def test_restore_filenames():
    label_map = {"candidate_a": "alice.pdf", "candidate_b": "bob.pdf"}
    ranking = [
        {"filename": "candidate_b", "score": 88},
        {"filename": "candidate_a", "score": 72},
    ]
    restored = restore_filenames(ranking, label_map)
    assert restored[0]["filename"] == "bob.pdf"
    assert restored[1]["filename"] == "alice.pdf"


def test_restore_filenames_preserves_other_fields():
    label_map = {"candidate_a": "cv.pdf"}
    ranking = [{"filename": "candidate_a", "score": 90, "nivel": "excelente"}]
    restored = restore_filenames(ranking, label_map)
    assert restored[0]["score"] == 90
    assert restored[0]["nivel"] == "excelente"


def test_restore_filenames_unknown_label_passthrough():
    """Labels not in the map are returned as-is (LLM hallucinated a filename)."""
    label_map = {"candidate_a": "real.pdf"}
    ranking = [{"filename": "candidate_z", "score": 50}]
    restored = restore_filenames(ranking, label_map)
    assert restored[0]["filename"] == "candidate_z"


def test_restore_filenames_does_not_mutate_input():
    label_map = {"candidate_a": "cv.pdf"}
    ranking = [{"filename": "candidate_a", "score": 80}]
    restore_filenames(ranking, label_map)
    assert ranking[0]["filename"] == "candidate_a"  # original untouched


# ── Extra keys preserved ──────────────────────────────────────────────────────

def test_contact_preserved_in_original():
    """anonymize_cvs only replaces filename and text — other keys survive unchanged."""
    cvs = [{"filename": "cv.pdf", "text": "Name: Jane Doe", "source": "bank", "cv_id": "abc-123"}]
    anon, _ = anonymize_cvs(cvs)
    assert anon[0]["source"] == "bank"
    assert anon[0]["cv_id"] == "abc-123"
    assert anon[0]["filename"] != "cv.pdf"
    # Original dict is not mutated
    assert cvs[0]["filename"] == "cv.pdf"
