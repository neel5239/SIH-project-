from services.m5_fusion.services.guardian import GuardianGate
from services.m5_fusion.services.summary_builder import SummaryBuilder


def test_guardian_blocks_diagnostic_summary_item():
    builder = SummaryBuilder()

    summary = builder.build(
        session_id="guardian-diagnostic",
        slots=[
            {
                "slot_id": "s1",
                "session_id": "guardian-diagnostic",
                "ontology_key": "general.chief_complaint",
                "value": "Patient has a diagnosis of migraine",
                "value_type": "string",
                "confidence": 1.0,
                "section": "chief_complaint",
                "answered_by": "self",
                "input_mode": "text",
                "provenance_id": "prov-1",
            }
        ],
    )

    assert summary.sections["chief_complaint"] == []
    assert summary.guardian.checked is True
    assert summary.guardian.blocked_count == 1


def test_guardian_blocks_therapeutic_summary_item():
    builder = SummaryBuilder()

    summary = builder.build(
        session_id="guardian-therapeutic",
        slots=[
            {
                "slot_id": "s1",
                "session_id": "guardian-therapeutic",
                "ontology_key": "general.chief_complaint",
                "value": "Recommend treatment with medication",
                "value_type": "string",
                "confidence": 1.0,
                "section": "chief_complaint",
                "answered_by": "self",
                "input_mode": "text",
                "provenance_id": "prov-1",
            }
        ],
    )

    assert summary.sections["chief_complaint"] == []
    assert summary.guardian.blocked_count == 1


def test_guardian_allows_clean_summary_item():
    builder = SummaryBuilder()

    summary = builder.build(
        session_id="guardian-clean",
        slots=[
            {
                "slot_id": "s1",
                "session_id": "guardian-clean",
                "ontology_key": "general.chief_complaint",
                "value": "Headache for three days",
                "value_type": "string",
                "confidence": 1.0,
                "section": "chief_complaint",
                "answered_by": "self",
                "input_mode": "text",
                "provenance_id": "prov-1",
            }
        ],
    )

    assert len(summary.sections["chief_complaint"]) == 1
    assert summary.guardian.checked is True
    assert summary.guardian.blocked_count == 0


def test_guardian_failure_fails_closed():
    class FailingGuardian:
        version = "g-failing"

        def check_or_fail_closed(self, text):
            raise RuntimeError("unexpected guardian failure")

    builder = SummaryBuilder(
        guardian=FailingGuardian()
    )

    summary = builder.build(
        session_id="guardian-failure",
        slots=[
            {
                "slot_id": "s1",
                "session_id": "guardian-failure",
                "ontology_key": "general.chief_complaint",
                "value": "Headache for three days",
                "value_type": "string",
                "confidence": 1.0,
                "section": "chief_complaint",
                "answered_by": "self",
                "input_mode": "text",
                "provenance_id": "prov-1",
            }
        ],
    )

    assert summary.sections["chief_complaint"] == []
    assert summary.guardian.checked is True
    assert summary.guardian.blocked_count == 1
    assert summary.guardian.version == "g-failing"
