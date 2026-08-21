import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from main import (
    extract_actionable_steps,
    diagnosis_contains_actionable_content,
    clean_markdown_step,
    normalize_section,
)

SAMPLE_EVIDENCE_MAP = {
    "S1": {"text": "Grafana Alloy logs show repeated HTTP 404 errors.", "source": "loki-alloy-404.md", "section": "Symptoms"},
    "S2": {"text": "Confirm the Loki endpoint includes /loki/api/v1/push.", "source": "loki-alloy-404.md", "section": "Remediation"},
    "S3": {"text": "Restart the Alloy service: `sudo systemctl restart alloy`", "source": "loki-alloy-404.md", "section": "Remediation"},
    "S4": {"text": "Confirm Alloy logs no longer show 404 errors.", "source": "loki-alloy-404.md", "section": "Validation"},
}


def test_symptoms_are_excluded_from_remediation():
    remediation, validation = extract_actionable_steps(SAMPLE_EVIDENCE_MAP)
    remediation_texts = [s["evidence"] for s in remediation]
    assert SAMPLE_EVIDENCE_MAP["S1"]["text"] not in remediation_texts, "A Symptoms line must never appear as a remediation step"


def test_remediation_steps_are_extracted():
    remediation, validation = extract_actionable_steps(SAMPLE_EVIDENCE_MAP)
    assert len(remediation) == 2
    assert any("Loki endpoint" in s["instruction"] for s in remediation)
    assert any("Restart" in s["instruction"] for s in remediation)


def test_validation_steps_are_extracted_separately():
    remediation, validation = extract_actionable_steps(SAMPLE_EVIDENCE_MAP)
    assert len(validation) == 1
    assert "404 errors" in validation[0]["instruction"]


def test_displayed_instruction_matches_evidence_text():
    remediation, validation = extract_actionable_steps(SAMPLE_EVIDENCE_MAP)
    restart_step = [s for s in remediation if "Restart" in s["instruction"]][0]
    assert restart_step["instruction"] == restart_step["evidence"], "Instruction must come directly from evidence text, never model-generated"


def test_diagnosis_with_command_is_flagged():
    diagnosis_with_command = "Run sudo systemctl restart alloy to fix this."
    assert diagnosis_contains_actionable_content(diagnosis_with_command) is True


def test_clean_diagnosis_is_not_flagged():
    clean_diagnosis = "The Alloy configuration is missing the correct Loki endpoint path."
    assert diagnosis_contains_actionable_content(clean_diagnosis) is False


def test_clean_markdown_step_strips_bullets_and_numbers():
    assert clean_markdown_step("- Restart the service") == "Restart the service"
    assert clean_markdown_step("3. Restart the service") == "Restart the service"
    assert clean_markdown_step("Restart the service") == "Restart the service"


def test_normalize_section_handles_variants():
    assert normalize_section("Remediation Steps") == "Remediation"
    assert normalize_section("Verification") == "Validation"
    assert normalize_section("Observed Symptoms") == "Symptoms"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])