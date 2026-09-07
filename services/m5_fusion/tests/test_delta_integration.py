from services.m5_fusion.services.summary_builder import SummaryBuilder


def test_delta_is_integrated_into_return_visit_summary():
    builder = SummaryBuilder()

    summary = builder.build(
        session_id="delta-integration",
        is_return_visit=True,
        visit_number=2,
        slots=[
            {
                "slot_id": "s1",
                "session_id": "delta-integration",
                "ontology_key": "general.symptom.headache",
                "value": "headache",
                "value_type": "string",
                "confidence": 1.0,
                "section": "hpi",
                "answered_by": "self",
                "input_mode": "text",
                "provenance_id": "prov-current",
            }
        ],
        prior_encounter={
            "symptoms": ["headache", "nausea"],
            "symptoms_provenance": ["prov-prior"],
        },
    )

    assert summary.delta.is_return_visit is True
    assert summary.delta.visit_number == 2
    assert "Symptom no longer reported: nausea" in summary.delta.changed
    assert "prov-current" in summary.delta.provenance
    assert "prov-prior" in summary.delta.provenance


def test_delta_is_skipped_when_no_prior_encounter():
    builder = SummaryBuilder()

    summary = builder.build(
        session_id="delta-no-prior",
        is_return_visit=True,
        visit_number=2,
        slots=[],
        prior_encounter=None,
    )

    assert summary.delta.is_return_visit is True
    assert summary.delta.visit_number == 2
    assert summary.delta.changed == []
    assert summary.delta.adherence_estimate is None


def test_adherence_is_integrated():
    builder = SummaryBuilder()

    summary = builder.build(
        session_id="delta-adherence",
        is_return_visit=True,
        prior_encounter={},
        slots=[
            {
                "slot_id": "s1",
                "session_id": "delta-adherence",
                "ontology_key": "general.adherence",
                "value": 90,
                "value_type": "number",
                "confidence": 1.0,
                "section": "hpi",
                "answered_by": "self",
                "input_mode": "text",
                "provenance_id": "prov-adherence",
            }
        ],
    )

    assert summary.delta.adherence_estimate == 90.0
    assert summary.delta.adherence_category == "good"
    assert summary.delta.adherence_reason is not None
    assert "estimate" in summary.delta.adherence_reason.lower()


def test_delta_does_not_invent_changes_without_comparable_data():
    builder = SummaryBuilder()

    summary = builder.build(
        session_id="delta-empty",
        is_return_visit=True,
        prior_encounter={},
        slots=[],
        entities=[],
    )

    assert summary.delta.changed == []
    assert summary.delta.adherence_estimate is None


def test_delta_provenance_is_preserved():
    builder = SummaryBuilder()

    summary = builder.build(
        session_id="delta-provenance",
        is_return_visit=True,
        prior_encounter={
            "severity": 8,
            "severity_provenance": ["prov-old"],
        },
        slots=[
            {
                "slot_id": "s1",
                "session_id": "delta-provenance",
                "ontology_key": "general.severity",
                "value": 4,
                "value_type": "number",
                "confidence": 1.0,
                "section": "hpi",
                "answered_by": "self",
                "input_mode": "text",
                "provenance_id": "prov-new",
            }
        ],
    )

    assert "Severity decreased: 8 -> 4" in summary.delta.changed
    assert "prov-new" in summary.delta.provenance
    assert "prov-old" in summary.delta.provenance
