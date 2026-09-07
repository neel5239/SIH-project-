from fastapi.testclient import TestClient

from services.m5_fusion.api import app
from services.m5_fusion.database.provenance_repository import ProvenanceRepository


client = TestClient(app)
provenance_repository = ProvenanceRepository()


def test_root_and_health():
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["service"] == "M5 Fusion, Summary & Safety"

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"


def test_naive_summary_vertical_slice():
    session_id = "m5-phase1-demo"

    provenance_repository.save({
        "prov_id": "prov-m3-001",
        "kind": "text",
        "session_id": session_id,
        "text": "chest pain",
    })

    provenance_repository.save({
        "prov_id": "prov-m3-002",
        "kind": "text",
        "session_id": session_id,
        "text": "3 days",
    })

    provenance_repository.save({
        "prov_id": "prov-m4-001",
        "kind": "image_bbox",
        "session_id": session_id,
        "source_ref": "doc-001",
    })

    response = client.post(
        f"/api/v1/session/{session_id}/summarise",
        json={
            "slots": [
                {
                    "ontology_key": "general.chief_complaint",
                    "value": "chest pain",
                    "section": "chief_complaint",
                    "confidence": 0.95,
                    "provenance_id": "prov-m3-001",
                    "answered_by": "self",
                },
                {
                    "ontology_key": "hpi.duration",
                    "value": "3 days",
                    "section": "hpi",
                    "confidence": 0.92,
                    "provenance_id": "prov-m3-002",
                    "answered_by": "self",
                },
            ],
            "entities": [
                {
                    "entity_id": "entity-001",
                    "document_id": "doc-001",
                    "document_type": "prescription",
                    "entity_type": "medicine",
                    "payload": {
                        "name": "Metformin",
                        "strength": 500,
                        "strength_unit": "mg",
                        "frequency": "BD",
                    },
                    "event_date": "2026-09-01",
                    "source": {
                        "type": "image_bbox",
                        "provenance_id": "prov-m4-001",
                    },
                }
            ],
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "draft"
    assert body["fields_generated"] == 3
    assert body["fields_dropped_unsourced"] == 0
    assert body["guardian_blocks"] == 0

    summary_id = body["summary_id"]

    fetched = client.get(
        f"/api/v1/session/{session_id}/summary"
    )

    assert fetched.status_code == 200

    summary = fetched.json()

    assert summary["summary_id"] == summary_id

    assert summary["sections"]["chief_complaint"] == [
        {
            "text": "chest pain",
            "provenance": ["prov-m3-001"],
            "answered_by": "self",
        }
    ]

    assert summary["sections"]["hpi"] == [
        {
            "text": "3 days",
            "provenance": ["prov-m3-002"],
            "answered_by": "self",
        }
    ]

    assert summary["sections"]["drugs"][0]["text"] == "Metformin 500 mg BD"
    assert summary["sections"]["drugs"][0]["provenance"] == [
        "prov-m4-001"
    ]

    assert summary["timeline"][0]["date"] == "2026-09-01"
    assert summary["timeline"][0]["provenance"] == ["prov-m4-001"]


def test_unsourced_fields_are_not_rendered():
    session_id = "m5-unsourced-demo"

    provenance_repository.save({
        "prov_id": "prov-good",
        "kind": "text",
        "session_id": session_id,
        "text": "headache",
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
                    "provenance_id": "prov-good",
                    "answered_by": "self",
                },
                {
                    "ontology_key": "hpi.character",
                    "value": "severe",
                    "section": "hpi",
                    "confidence": 0.95,
                    "answered_by": "self",
                },
            ],
            "entities": [],
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["fields_generated"] == 1
    assert body["fields_dropped_unsourced"] == 1

    summary = client.get(
        f"/api/v1/session/{session_id}/summary"
    ).json()

    assert len(summary["sections"]["chief_complaint"]) == 1
    assert summary["sections"]["hpi"] == []


def test_return_visit_without_prior_encounter_does_not_fabricate_delta():
    session_id = "m5-return-demo"

    response = client.post(
        f"/api/v1/session/{session_id}/summarise",
        json={
            "is_return_visit": True,
            "visit_number": 3,
            "prior_encounter": None,
            "slots": [
                {
                    "ontology_key": "general.chief_complaint",
                    "value": "cough",
                    "section": "chief_complaint",
                    "provenance_id": "prov-001",
                    "answered_by": "self",
                }
            ],
            "entities": [],
        },
    )

    assert response.status_code == 200

    summary = client.get(
        f"/api/v1/session/{session_id}/summary"
    ).json()

    assert summary["delta"]["is_return_visit"] is True
    assert summary["delta"]["visit_number"] == 3
    assert summary["delta"]["changed"] == []
    assert summary["delta"]["adherence_estimate"] is None


def test_missing_summary_returns_404():
    response = client.get(
        "/api/v1/session/session-that-does-not-exist/summary"
    )

    assert response.status_code == 404

def test_conflict_is_exposed_in_summary():
    session_id = "m5-conflict-demo"

    response = client.post(
        f"/api/v1/session/{session_id}/summarise",
        json={
            "slots": [
                {
                    "ontology_key": "vitals.weight",
                    "value": "60 kg",
                    "provenance_id": "audio-weight",
                }
            ],
            "entities": [
                {
                    "ontology_key": "vitals.weight",
                    "entity_type": "vital",
                    "payload": {"text": "78 kg"},
                    "provenance_id": "image-weight",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["conflicts_detected"] == 1

    summary = client.get(
        f"/api/v1/session/{session_id}/summary"
    ).json()

    assert len(summary["conflicts"]) == 1
    assert summary["conflicts"][0]["key"] == "vitals.weight"
    assert summary["conflicts"][0]["conflict_type"] == (
        "contradictory_values"
    )

    values = [
        fact["value"]
        for fact in summary["conflicts"][0]["facts"]
    ]

    assert "60 kg" in values
    assert "78 kg" in values

    assert len(summary["alerts"]) == 1




