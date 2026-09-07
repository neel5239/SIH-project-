from fastapi.testclient import TestClient

from services.m5_fusion.api import app


client = TestClient(app)


def test_dual_coding_is_integrated_into_summary():
    response = client.post(
        "/api/v1/session/coding-1/summarise",
        json={
            "slots": [
                {
                    "slot_id": "c1",
                    "ontology_key": "ayush.condition",
                    "value": "Amlapitta",
                    "value_type": "string",
                    "confidence": 1.0,
                    "section": "hpi",
                    "answered_by": "self",
                    "input_mode": "touch",
                    "provenance_id": "prov-c1",
                }
            ]
        },
    )

    assert response.status_code == 200

    summary = client.get(
        "/api/v1/session/coding-1/summary"
    )

    assert summary.status_code == 200

    data = summary.json()

    assert data["ayush"]["codes"]["namaste"] == "AAE-16"
    assert data["ayush"]["codes"]["icd11_tm2"] == "SF7Y"


def test_unknown_condition_does_not_get_fabricated_code():
    response = client.post(
        "/api/v1/session/coding-2/summarise",
        json={
            "slots": [
                {
                    "slot_id": "c1",
                    "ontology_key": "ayush.condition",
                    "value": "Unknown Ayurveda Condition XYZ",
                    "value_type": "string",
                    "confidence": 1.0,
                    "section": "hpi",
                    "answered_by": "self",
                    "input_mode": "touch",
                    "provenance_id": "prov-c1",
                }
            ]
        },
    )

    assert response.status_code == 200

    data = client.get(
        "/api/v1/session/coding-2/summary"
    ).json()

    assert data["ayush"]["codes"]["namaste"] is None
    assert data["ayush"]["codes"]["icd11_tm2"] is None


def test_unsourced_condition_does_not_get_code():
    response = client.post(
        "/api/v1/session/coding-3/summarise",
        json={
            "slots": [
                {
                    "slot_id": "c1",
                    "ontology_key": "ayush.condition",
                    "value": "Amlapitta",
                    "value_type": "string",
                    "confidence": 1.0,
                    "section": "hpi",
                    "answered_by": "self",
                    "input_mode": "touch",
                }
            ]
        },
    )

    assert response.status_code == 200

    data = client.get(
        "/api/v1/session/coding-3/summary"
    ).json()

    assert data["ayush"]["codes"]["namaste"] is None
    assert data["ayush"]["codes"]["icd11_tm2"] is None
