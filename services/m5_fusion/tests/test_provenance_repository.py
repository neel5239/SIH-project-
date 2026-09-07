from services.m5_fusion.database.provenance_repository import (
    ProvenanceRepository,
)


def test_save_and_get_provenance():
    repo = ProvenanceRepository()

    repo.delete("prov-mongo-1")

    record = {
        "prov_id": "prov-mongo-1",
        "kind": "transcript",
        "session_id": "session-1",
        "text": "Patient reports headache",
    }

    repo.save(record)

    loaded = repo.get("prov-mongo-1")

    assert loaded is not None
    assert loaded["prov_id"] == "prov-mongo-1"
    assert loaded["kind"] == "transcript"
    assert loaded["text"] == "Patient reports headache"

    repo.delete("prov-mongo-1")


def test_provenance_exists():
    repo = ProvenanceRepository()

    repo.delete("prov-mongo-2")

    assert repo.exists("prov-mongo-2") is False

    repo.save({
        "prov_id": "prov-mongo-2",
        "kind": "physician_entry",
        "session_id": "session-2",
    })

    assert repo.exists("prov-mongo-2") is True

    repo.delete("prov-mongo-2")


def test_missing_provenance_returns_none():
    repo = ProvenanceRepository()

    repo.delete("prov-mongo-missing")

    assert repo.get("prov-mongo-missing") is None


def test_delete_provenance():
    repo = ProvenanceRepository()

    repo.save({
        "prov_id": "prov-mongo-3",
        "kind": "text",
        "session_id": "session-3",
    })

    assert repo.delete("prov-mongo-3") is True
    assert repo.get("prov-mongo-3") is None
