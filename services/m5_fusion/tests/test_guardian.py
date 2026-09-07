import pytest

from services.m5_fusion.services.guardian import (
    GuardianError,
    GuardianGate,
)


def test_clean_content_is_allowed():
    guardian = GuardianGate()

    result = guardian.check(
        "Patient reports headache for three days."
    )

    assert result.label == "clean"
    assert result.allowed is True
    assert result.text == "Patient reports headache for three days."


def test_diagnostic_content_is_blocked():
    guardian = GuardianGate()

    result = guardian.check(
        "Patient has a diagnosis of migraine."
    )

    assert result.label == "diagnostic"
    assert result.allowed is False
    assert "diagnostic" in result.reason.lower()


def test_therapeutic_content_is_blocked():
    guardian = GuardianGate()

    result = guardian.check(
        "Recommend treatment with medication."
    )

    assert result.label == "therapeutic"
    assert result.allowed is False


def test_prescription_content_is_blocked():
    guardian = GuardianGate()

    result = guardian.check(
        "Prescribe the medicine twice daily."
    )

    assert result.label == "therapeutic"
    assert result.allowed is False


def test_likely_diagnosis_is_blocked():
    guardian = GuardianGate()

    result = guardian.check(
        "The symptoms are likely migraine."
    )

    assert result.label == "diagnostic"
    assert result.allowed is False


def test_normalization_handles_case_and_whitespace():
    guardian = GuardianGate()

    result = guardian.check(
        "   PATIENT   HAS A DIAGNOSIS OF MIGRAINE   "
    )

    assert result.label == "diagnostic"
    assert result.allowed is False


def test_multiple_checks_update_metrics():
    guardian = GuardianGate()

    guardian.check("Patient reports fatigue.")
    guardian.check("Patient has a diagnosis of anemia.")
    guardian.check("Recommend treatment with medication.")

    metrics = guardian.metrics()

    assert metrics["outputs_checked"] == 3
    assert metrics["blocked_diagnostic"] == 1
    assert metrics["blocked_therapeutic"] == 1
    assert metrics["blocked_total"] == 2
    assert metrics["emitted_diagnostic"] == 0
    assert metrics["emitted_therapeutic"] == 0


def test_empty_text_fails_closed():
    guardian = GuardianGate()

    result = guardian.check_or_fail_closed("")

    assert result.allowed is False
    assert result.label == "blocked"
    assert "failure" in result.reason.lower()


def test_invalid_input_fails_closed():
    guardian = GuardianGate()

    result = guardian.check_or_fail_closed(None)

    assert result.allowed is False
    assert result.label == "blocked"


def test_custom_guardian_version_is_preserved():
    guardian = GuardianGate(version="g-test-1.0")

    result = guardian.check("Patient reports fatigue.")

    assert result.version == "g-test-1.0"
    assert guardian.metrics()["guardian_version"] == "g-test-1.0"


def test_reset_metrics():
    guardian = GuardianGate()

    guardian.check("Patient has a diagnosis.")
    guardian.check("Recommend treatment.")

    assert guardian.metrics()["outputs_checked"] == 2

    guardian.reset_metrics()

    metrics = guardian.metrics()

    assert metrics["outputs_checked"] == 0
    assert metrics["blocked_diagnostic"] == 0
    assert metrics["blocked_therapeutic"] == 0


def test_guardian_error_type_exists():
    assert issubclass(GuardianError, RuntimeError)


def test_clean_content_is_returned_unchanged():
    guardian = GuardianGate()

    text = "Patient reports mild abdominal discomfort."

    result = guardian.check(text)

    assert result.text == text
    assert result.allowed is True
