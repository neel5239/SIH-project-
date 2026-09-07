from fastapi.testclient import TestClient

from services.m5_fusion.api import app
from services.m5_fusion.database.provenance_repository import (
    ProvenanceRepository,
)
from services.m5_fusion.database.summary_repository import SummaryRepository


client = TestClient(app)

summary_repository = SummaryRepository()
provenance_repository = ProvenanceRepository()


def test_provenance_lookup_returns_linked_record():
    session_id = "provenance-api-test"

    provenance_repository.save({
        "prov_id": "prov-api-001",
        "kind": "transcript",
        "session_id": session_id,
        "text": "Patient reports headache",
    })

    response = client.post(
        f"/api/v1/session/{session_id}/summarise",
        json={
            "slots": [
                {
                    "ontology_key": "general.chief_complaint",
                    "value": "headache",
                    "section": "chief_complaint",
                    "confidence": 0.95,
                    "provenance_id": "prov-api-001",
                    "answered_by": "self",
                }
            ],
            "entities": [],
        },
    )

    assert response.status_code == 200

    summary = summary_repository.get(session_id)

    assert summary is not None
    assert "prov-api-001" in summary.sections["chief_complaint"][0].provenance

    response = client.get(
        f"/api/v1/summary/{summary.summary_id}/provenance/prov-api-001"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["prov_id"] == "prov-api-001"
    assert data["kind"] == "transcript"
    assert data["text"] == "Patient reports headache"


def test_provenance_lookup_rejects_unlinked_record():
    session_id = "provenance-api-unlinked"

    provenance_repository.save({
        "prov_id": "prov-unlinked-001",
        "kind": "transcript",
        "session_id": session_id,
        "text": "Unlinked provenance",
    })

    response = client.post(
        f"/api/v1/session/{session_id}/summarise",
        json={
            "slots": [
                {
                    "ontology_key": "general.chief_complaint",
                    "value": "cough",
                    "section": "chief_complaint",
                    "confidence": 0.95,
                    "provenance_id": "different-prov",
                    "answered_by": "self",
                }
            ],
            "entities": [],
        },
    )

    assert response.status_code == 200

    summary = summary_repository.get(session_id)

    assert summary is not None

    response = client.get(
        f"/api/v1/summary/{summary.summary_id}/provenance/prov-unlinked-001"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Provenance not linked to summary"


def test_provenance_lookup_returns_404_for_missing_provenance():
    session_id = "provenance-api-missing"

    response = client.post(
        f"/api/v1/session/{session_id}/summarise",
        json={
            "slots": [
                {
                    "ontology_key": "general.chief_complaint",
                    "value": "fever",
                    "section": "chief_complaint",
                    "confidence": 0.95,
                    "provenance_id": "prov-existing-summary",
                    "answered_by": "self",
                }
            ],
            "entities": [],
        },
    )

    assert response.status_code == 200

    summary = summary_repository.get(session_id)

    assert summary is not None

    response = client.get(
        f"/api/v1/summary/{summary.summary_id}/provenance/prov-does-not-exist"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Provenance not found"

def test_provenance_request_is_persisted_and_field_is_rendered():
    session_id = "provenance-persist-test"

    response = client.post(
        f"/api/v1/session/{session_id}/summarise",
        json={
            "provenance": [
                {
                    "prov_id": "prov-persist-001",
                    "kind": "transcript",
                    "session_id": session_id,
                    "text": "Patient reports nausea",
                }
            ],
            "slots": [
                {
                    "ontology_key": "general.chief_complaint",
                    "value": "nausea",
                    "section": "chief_complaint",
                    "confidence": 0.95,
                    "provenance_id": "prov-persist-001",
                    "answered_by": "self",
                }
            ],
            "entities": [],
        },
    )

    assert response.status_code == 200

    summary = summary_repository.get(session_id)

    assert summary is not None
    assert len(summary.sections["chief_complaint"]) == 1
    assert (
        summary.sections["chief_complaint"][0].provenance
        == ["prov-persist-001"]
    )

    stored = provenance_repository.get("prov-persist-001")

    assert stored is not None
    assert stored["kind"] == "transcript"


def test_missing_provenance_is_silently_dropped():
    session_id = "provenance-missing-safety"

    response = client.post(
        f"/api/v1/session/{session_id}/summarise",
        json={
            "slots": [
                {
                    "ontology_key": "general.chief_complaint",
                    "value": "dizziness",
                    "section": "chief_complaint",
                    "confidence": 0.95,
                    "provenance_id": "prov-never-supplied",
                    "answered_by": "self",
                }
            ],
            "entities": [],
            "provenance": [],
        },
    )

    assert response.status_code == 200

    summary = summary_repository.get(session_id)

    assert summary is not None
    assert summary.sections["chief_complaint"] == []


def test_invalid_provenance_kind_is_dropped():
    session_id = "provenance-invalid-kind"

    response = client.post(
        f"/api/v1/session/{session_id}/summarise",
        json={
            "provenance": [
                {
                    "prov_id": "prov-invalid-kind",
                    "kind": "unsupported_source_type",
                    "session_id": session_id,
                }
            ],
            "slots": [
                {
                    "ontology_key": "general.chief_complaint",
                    "value": "pain",
                    "section": "chief_complaint",
                    "confidence": 0.95,
                    "provenance_id": "prov-invalid-kind",
                    "answered_by": "self",
                }
            ],
            "entities": [],
        },
    )

    assert response.status_code == 200

    summary = summary_repository.get(session_id)

    assert summary is not None
    assert summary.sections["chief_complaint"] == []


def test_audio_provenance_without_retention_requires_transcript():
    session_id = "provenance-audio-safety"

    response = client.post(
        f"/api/v1/session/{session_id}/summarise",
        json={
            "provenance": [
                {
                    "prov_id": "prov-audio-no-retain",
                    "kind": "audio_offset",
                    "session_id": session_id,
                    "retain_audio": False,
                }
            ],
            "slots": [
                {
                    "ontology_key": "general.chief_complaint",
                    "value": "cough",
                    "section": "chief_complaint",
                    "confidence": 0.95,
                    "provenance_id": "prov-audio-no-retain",
                    "answered_by": "self",
                }
            ],
            "entities": [],
        },
    )

    assert response.status_code == 200

    summary = summary_repository.get(session_id)

    assert summary is not None
    assert summary.sections["chief_complaint"] == []
