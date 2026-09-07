from services.m5_fusion.services.delta_engine import (
    DeltaEngine,
)


def test_no_prior_encounter_skips_delta():
    engine = DeltaEngine()

    result = engine.compare(
        current={"symptoms": ["headache"]},
        prior=None,
        is_return_visit=True,
        visit_number=2,
    )

    assert result.is_return_visit is True
    assert result.changed == ()
    assert result.adherence_estimate is None


def test_non_return_visit_skips_delta():
    engine = DeltaEngine()

    result = engine.compare(
        current={"symptoms": ["headache"]},
        prior={"symptoms": ["cough"]},
        is_return_visit=False,
    )

    assert result.changed == ()


def test_new_symptom_is_detected():
    engine = DeltaEngine()

    result = engine.compare(
        current={
            "symptoms": ["headache", "nausea"],
            "symptoms_provenance": ["prov-current"],
        },
        prior={
            "symptoms": ["headache"],
            "symptoms_provenance": ["prov-prior"],
        },
        is_return_visit=True,
        visit_number=2,
    )

    assert "New symptom reported: nausea" in result.changed
    assert "prov-current" in result.provenance
    assert "prov-prior" in result.provenance


def test_resolved_symptom_is_detected():
    engine = DeltaEngine()

    result = engine.compare(
        current={
            "symptoms": ["headache"],
        },
        prior={
            "symptoms": ["headache", "nausea"],
        },
        is_return_visit=True,
    )

    assert "Symptom no longer reported: nausea" in result.changed


def test_persistent_symptom_is_detected():
    engine = DeltaEngine()

    result = engine.compare(
        current={"symptoms": ["headache"]},
        prior={"symptoms": ["headache"]},
        is_return_visit=True,
    )

    assert "Symptom persists: headache" in result.changed


def test_severity_increase_is_detected():
    engine = DeltaEngine()

    result = engine.compare(
        current={
            "severity": 8,
            "severity_provenance": ["prov-current"],
        },
        prior={
            "severity": 4,
            "severity_provenance": ["prov-prior"],
        },
        is_return_visit=True,
    )

    assert "Severity increased: 4 -> 8" in result.changed


def test_severity_decrease_is_detected():
    engine = DeltaEngine()

    result = engine.compare(
        current={"severity": 3},
        prior={"severity": 7},
        is_return_visit=True,
    )

    assert "Severity decreased: 7 -> 3" in result.changed


def test_new_drug_is_detected():
    engine = DeltaEngine()

    result = engine.compare(
        current={
            "drugs": ["Drug A", "Drug B"],
            "drugs_provenance": ["prov-drugs"],
        },
        prior={
            "drugs": ["Drug A"],
        },
        is_return_visit=True,
    )

    assert "Drug newly reported: Drug B" in result.changed


def test_removed_drug_is_detected():
    engine = DeltaEngine()

    result = engine.compare(
        current={"drugs": ["Drug A"]},
        prior={"drugs": ["Drug A", "Drug B"]},
        is_return_visit=True,
    )

    assert "Drug no longer reported: Drug B" in result.changed


def test_lab_increase_is_detected():
    engine = DeltaEngine()

    result = engine.compare(
        current={
            "labs": {"hemoglobin": 12.5},
            "labs_provenance": ["prov-lab-current"],
        },
        prior={
            "labs": {"hemoglobin": 11.0},
            "labs_provenance": ["prov-lab-prior"],
        },
        is_return_visit=True,
    )

    assert (
        "Lab hemoglobin increased: 11.0 -> 12.5"
        in result.changed
    )


def test_lab_decrease_is_detected():
    engine = DeltaEngine()

    result = engine.compare(
        current={
            "labs": {"hemoglobin": 10.0},
        },
        prior={
            "labs": {"hemoglobin": 13.0},
        },
        is_return_visit=True,
    )

    assert (
        "Lab hemoglobin decreased: 13.0 -> 10.0"
        in result.changed
    )


def test_dosing_adherence_above_80_is_good():
    engine = DeltaEngine()

    result = engine.compare(
        current={"dosing_adherence": 90},
        prior={},
        is_return_visit=True,
    )

    assert result.adherence_estimate == 90.0
    assert result.adherence_category == "good"
    assert "patient dosing report" in result.adherence_reason


def test_adherence_between_40_and_80_is_partial():
    engine = DeltaEngine()

    result = engine.compare(
        current={"dosing_adherence": 60},
        prior={},
        is_return_visit=True,
    )

    assert result.adherence_estimate == 60.0
    assert result.adherence_category == "partial"


def test_adherence_below_40_is_poor():
    engine = DeltaEngine()

    result = engine.compare(
        current={"dosing_adherence": 25},
        prior={},
        is_return_visit=True,
    )

    assert result.adherence_estimate == 25.0
    assert result.adherence_category == "poor"


def test_dosing_and_refill_are_averaged():
    engine = DeltaEngine()

    result = engine.compare(
        current={
            "dosing_adherence": 90,
            "refill_adherence": 70,
        },
        prior={},
        is_return_visit=True,
    )

    assert result.adherence_estimate == 80.0
    assert result.adherence_category == "partial"


def test_adherence_is_explicitly_an_estimate():
    engine = DeltaEngine()

    result = engine.compare(
        current={"dosing_adherence": 90},
        prior={},
        is_return_visit=True,
    )

    assert "estimate" in result.adherence_reason.lower()
    assert "not a confirmed fact" in result.adherence_reason.lower()


def test_boolean_adherence_is_not_accepted():
    engine = DeltaEngine()

    result = engine.compare(
        current={"dosing_adherence": True},
        prior={},
        is_return_visit=True,
    )

    assert result.adherence_estimate is None
    assert result.adherence_category is None


def test_adherence_is_clamped():
    engine = DeltaEngine()

    result = engine.compare(
        current={"dosing_adherence": 150},
        prior={},
        is_return_visit=True,
    )

    assert result.adherence_estimate == 100.0
    assert result.adherence_category == "good"


def test_provenance_is_deduplicated():
    engine = DeltaEngine()

    result = engine.compare(
        current={
            "symptoms": ["headache"],
            "symptoms_provenance": ["prov-1"],
        },
        prior={
            "symptoms": ["headache"],
            "symptoms_provenance": ["prov-1"],
        },
        is_return_visit=True,
    )

    assert result.provenance == ("prov-1",)


def test_result_to_dict_is_serializable():
    engine = DeltaEngine()

    result = engine.compare(
        current={
            "symptoms": ["headache", "nausea"],
            "dosing_adherence": 85,
        },
        prior={
            "symptoms": ["headache"],
        },
        is_return_visit=True,
        visit_number=2,
    )

    data = result.to_dict()

    assert data["is_return_visit"] is True
    assert data["visit_number"] == 2
    assert isinstance(data["changed"], list)
    assert data["adherence_estimate"] == 85.0


def test_unknown_values_do_not_create_changes():
    engine = DeltaEngine()

    result = engine.compare(
        current={
            "symptoms": "unknown",
            "severity": "unknown",
            "drugs": None,
            "labs": None,
        },
        prior={
            "symptoms": ["headache"],
            "severity": 5,
        },
        is_return_visit=True,
    )

    assert result.changed == (
        "Symptom no longer reported: headache",
    )
