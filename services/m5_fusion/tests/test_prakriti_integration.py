from fastapi.testclient import TestClient

from services.m5_fusion.api import app


client = TestClient(app)


def test_prakriti_is_integrated_into_summary():
    response = client.post(
        "/api/v1/session/prakriti-1/summarise",
        json={
            "slots": [
                {
                    "slot_id": "p1",
                    "ontology_key": "ayush.prakriti.dosha_tendency",
                    "value": "vata",
                    "value_type": "string",
                    "confidence": 1.0,
                    "section": "personal_history",
                    "answered_by": "self",
                    "input_mode": "touch",
                    "provenance_id": "prov-p1",
                },
                {
                    "slot_id": "p2",
                    "ontology_key": "ayush.prakriti.characteristic",
                    "value": "pitta",
                    "value_type": "string",
                    "confidence": 1.0,
                    "section": "personal_history",
                    "answered_by": "self",
                    "input_mode": "touch",
                    "provenance_id": "prov-p2",
                },
            ]
        },
    )

    assert response.status_code == 200

    summary_response = client.get(
        "/api/v1/session/prakriti-1/summary"
    )

    assert summary_response.status_code == 200

    data = summary_response.json()
    prakriti = data["ayush"]["prakriti"]

    assert round(
        prakriti["vata"]
        + prakriti["pitta"]
        + prakriti["kapha"],
        6,
    ) == 1.0

    assert prakriti["items_total"] == 2
    assert prakriti["items_answered"] == 2
    assert prakriti["confidence"] >= 0.0
    assert prakriti["confidence"] <= 1.0
    assert prakriti["provisional"] is True
    assert "prov-p1" in prakriti["provenance"]
    assert "prov-p2" in prakriti["provenance"]


def test_prakriti_endpoint_returns_summary_result():
    response = client.post(
        "/api/v1/session/prakriti-2/summarise",
        json={
            "slots": [
                {
                    "slot_id": "p1",
                    "ontology_key": "ayush.prakriti.dosha_tendency",
                    "value": "kapha",
                    "confidence": 1.0,
                    "section": "personal_history",
                    "answered_by": "self",
                    "input_mode": "touch",
                    "provenance_id": "prov-k1",
                }
            ]
        },
    )

    assert response.status_code == 200

    prakriti_response = client.get(
        "/api/v1/session/prakriti-2/prakriti"
    )

    assert prakriti_response.status_code == 200

    data = prakriti_response.json()

    assert data["kapha"] == 1.0
    assert data["vata"] == 0.0
    assert data["pitta"] == 0.0
    assert data["dominant"] == "kapha"
    assert data["items_total"] == 1
    assert data["items_answered"] == 1


def test_unsourced_prakriti_slot_is_not_scored():
    response = client.post(
        "/api/v1/session/prakriti-3/summarise",
        json={
            "slots": [
                {
                    "slot_id": "p1",
                    "ontology_key": "ayush.prakriti.dosha_tendency",
                    "value": "vata",
                    "confidence": 1.0,
                    "section": "personal_history",
                    "answered_by": "self",
                    "input_mode": "touch",
                }
            ]
        },
    )

    assert response.status_code == 200

    data = client.get(
        "/api/v1/session/prakriti-3/prakriti"
    ).json()

    assert data["items_total"] == 0
    assert data["items_answered"] == 0
    assert data["confidence"] == 0.0
    assert data["provisional"] is True
    assert data["provenance"] == []
