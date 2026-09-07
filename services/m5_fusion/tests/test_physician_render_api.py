from fastapi.testclient import TestClient

from services.m5_fusion.api import app


client = TestClient(app)


def test_physician_render_endpoint_requires_existing_summary():
    response = client.get(
        "/api/v1/session/missing-session/physician-render"
    )

    assert response.status_code == 404


def test_physician_render_endpoint_returns_summary_render():
    session_id = "physician-api-test"

    response = client.post(
        f"/api/v1/session/{session_id}/summarise",
        json={
            "slots": [
                {
                    "slot_id": "s1",
                    "session_id": session_id,
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
            "entities": [],
        },
    )

    assert response.status_code == 200

    render_response = client.get(
        f"/api/v1/session/{session_id}/physician-render"
    )

    assert render_response.status_code == 200

    data = render_response.json()

    assert "sections" in data
    assert "Chief Complaint" in data["sections"]
    assert data["sections"]["Chief Complaint"] == [
        "Headache for three days [source: prov-1]"
    ]


def test_physician_text_endpoint_returns_plain_text():
    session_id = "physician-text-api-test"

    response = client.post(
        f"/api/v1/session/{session_id}/summarise",
        json={
            "slots": [
                {
                    "slot_id": "s1",
                    "session_id": session_id,
                    "ontology_key": "general.chief_complaint",
                    "value": "Fever for two days",
                    "value_type": "string",
                    "confidence": 1.0,
                    "section": "chief_complaint",
                    "answered_by": "proxy",
                    "input_mode": "text",
                    "provenance_id": "prov-fever",
                }
            ],
            "entities": [],
        },
    )

    assert response.status_code == 200

    render_response = client.get(
        f"/api/v1/session/{session_id}/physician-render/text"
    )

    assert render_response.status_code == 200

    data = render_response.json()

    assert "text" in data
    assert "Fever for two days" in data["text"]
    assert "[PROXY]" in data["text"]
    assert "[source: prov-fever]" in data["text"]


def test_physician_render_can_hide_ayush():
    session_id = "physician-ayush-hidden"

    response = client.post(
        f"/api/v1/session/{session_id}/summarise",
        json={
            "slots": [],
            "entities": [],
        },
    )

    assert response.status_code == 200

    render_response = client.get(
        f"/api/v1/session/{session_id}/physician-render",
        params={"ayush_opd": "false"},
    )

    assert render_response.status_code == 200
    assert render_response.json()["ayush"] == {}


def test_physician_render_preserves_guardian_blocking():
    session_id = "physician-guardian-api"

    response = client.post(
        f"/api/v1/session/{session_id}/summarise",
        json={
            "slots": [
                {
                    "slot_id": "s1",
                    "session_id": session_id,
                    "ontology_key": "general.chief_complaint",
                    "value": "Patient has a diagnosis of migraine",
                    "value_type": "string",
                    "confidence": 1.0,
                    "section": "chief_complaint",
                    "answered_by": "self",
                    "input_mode": "text",
                    "provenance_id": "prov-diagnostic",
                }
            ],
            "entities": [],
        },
    )

    assert response.status_code == 200

    summary_response = client.get(
        f"/api/v1/session/{session_id}/summary"
    )

    assert summary_response.status_code == 200

    summary = summary_response.json()

    assert summary["sections"]["chief_complaint"] == []
    assert summary["guardian"]["checked"] is True
    assert summary["guardian"]["blocked_count"] == 1

    render_response = client.get(
        f"/api/v1/session/{session_id}/physician-render"
    )

    assert render_response.status_code == 200
    assert render_response.json()["sections"]["Chief Complaint"] == []
