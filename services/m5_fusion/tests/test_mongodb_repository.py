from services.m5_fusion.database.mongo import mongo
from services.m5_fusion.database.summary_repository import (
    SummaryRepository,
)
from services.m5_fusion.models import ClinicalSummary, SummaryItem


def test_mongodb_ping():
    assert mongo.ping() is True


def test_save_and_get_summary():
    repo = SummaryRepository()

    repo.delete("mongo-test-1")

    summary = ClinicalSummary(
        session_id="mongo-test-1",
    )

    summary.sections["chief_complaint"].append(
        SummaryItem(
            text="Headache",
            provenance=["prov-1"],
            answered_by="self",
        )
    )

    repo.save(summary)

    loaded = repo.get("mongo-test-1")

    assert loaded is not None
    assert loaded.session_id == "mongo-test-1"
    assert loaded.sections["chief_complaint"][0].text == "Headache"

    repo.delete("mongo-test-1")


def test_repository_exists():
    repo = SummaryRepository()

    repo.delete("mongo-test-2")

    assert repo.exists("mongo-test-2") is False

    summary = ClinicalSummary(
        session_id="mongo-test-2",
    )

    repo.save(summary)

    assert repo.exists("mongo-test-2") is True

    repo.delete("mongo-test-2")


def test_repository_delete():
    repo = SummaryRepository()

    summary = ClinicalSummary(
        session_id="mongo-test-3",
    )

    repo.save(summary)

    assert repo.delete("mongo-test-3") is True
    assert repo.get("mongo-test-3") is None
