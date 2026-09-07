from services.m5_fusion.services.conflict_resolver import ConflictResolver


def test_denial_vs_documentary_evidence_is_not_merged():
    resolver = ConflictResolver()

    conflicts = resolver.resolve(
        slots=[
            {
                "ontology_key": "past_medical.diabetes",
                "value": False,
                "provenance_id": "audio-001",
            }
        ],
        entities=[
            {
                "entity_type": "medicine",
                "payload": {
                    "name": "Metformin",
                    "strength": 500,
                    "strength_unit": "mg",
                    "frequency": "BD",
                },
                "provenance_id": "image-001",
            }
        ],
    )

    assert conflicts == []

    conflicts = resolver.resolve(
        slots=[
            {
                "ontology_key": "past_medical.diabetes",
                "value": False,
                "provenance_id": "audio-001",
            }
        ],
        entities=[
            {
                "ontology_key": "past_medical.diabetes",
                "entity_type": "diagnosis",
                "payload": {"text": "diabetes"},
                "provenance_id": "image-001",
            }
        ],
    )

    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "denial_vs_documentary"
    assert len(conflicts[0].facts) == 2
    assert conflicts[0].facts[0].provenance == ["audio-001"]
    assert conflicts[0].facts[1].provenance == ["image-001"]


def test_contradictory_values_are_both_preserved():
    resolver = ConflictResolver()

    conflicts = resolver.resolve(
        slots=[
            {
                "ontology_key": "vitals.weight",
                "value": "60 kg",
                "provenance_id": "audio-weight",
            }
        ],
        entities=[
            {
                "ontology_key": "vitals.weight",
                "entity_type": "vital",
                "payload": {"text": "78 kg"},
                "provenance_id": "image-weight",
                "event_date": "2026-06-01",
            }
        ],
    )

    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "contradictory_values"

    values = [fact.value for fact in conflicts[0].facts]

    assert "60 kg" in values
    assert "78 kg" in values


def test_matching_values_are_not_reported_as_conflict():
    resolver = ConflictResolver()

    conflicts = resolver.resolve(
        slots=[
            {
                "ontology_key": "vitals.weight",
                "value": "60 kg",
                "provenance_id": "audio-weight",
            }
        ],
        entities=[
            {
                "ontology_key": "vitals.weight",
                "entity_type": "vital",
                "payload": {"text": "60 kg"},
                "provenance_id": "image-weight",
            }
        ],
    )

    assert conflicts == []


def test_drug_list_mismatch_is_detected():
    resolver = ConflictResolver()

    conflicts = resolver.resolve(
        slots=[
            {
                "ontology_key": "drugs.current",
                "value": ["Metformin", "Amlodipine"],
                "provenance_id": "audio-drugs",
            }
        ],
        entities=[
            {
                "entity_type": "medicine",
                "payload": {"name": "Metformin"},
                "provenance_id": "rx-001",
            },
            {
                "entity_type": "medicine",
                "payload": {"name": "Amlodipine"},
                "provenance_id": "rx-002",
            },
            {
                "entity_type": "medicine",
                "payload": {"name": "Telmisartan"},
                "provenance_id": "rx-003",
            },
        ],
    )

    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "drug_list_mismatch"

    assert conflicts[0].facts[0].value == [
        "amlodipine",
        "metformin",
    ]

    assert conflicts[0].facts[1].value == [
        "amlodipine",
        "metformin",
        "telmisartan",
    ]
