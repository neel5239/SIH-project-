from services.m5_fusion.services.provenance_binder import (
    ProvenanceBinder,
)


def test_valid_provenance_is_retained():
    binder = ProvenanceBinder(
        {
            "prov-1": {
                "prov_id": "prov-1",
                "kind": "physician_entry",
            }
        }
    )

    result = binder.bind_and_filter(
        [
            {
                "text": "Headache for three days",
                "provenance": ["prov-1"],
                "answered_by": "self",
            }
        ]
    )

    assert len(result) == 1
    assert result[0].text == "Headache for three days"
    assert result[0].provenance == ("prov-1",)
    assert result[0].answered_by == "self"
    assert binder.dropped_count == 0


def test_missing_provenance_is_silently_dropped():
    binder = ProvenanceBinder({})

    result = binder.bind_and_filter(
        [
            {
                "text": "Unsourced clinical fact",
                "provenance": [],
            }
        ]
    )

    assert result == []
    assert binder.dropped_count == 1


def test_unknown_provenance_reference_is_dropped():
    binder = ProvenanceBinder(
        {
            "prov-valid": {
                "prov_id": "prov-valid",
                "kind": "physician_entry",
            }
        }
    )

    result = binder.bind_and_filter(
        [
            {
                "text": "Sourced fact",
                "provenance": ["prov-unknown"],
            }
        ]
    )

    assert result == []
    assert binder.dropped_count == 1


def test_invalid_provenance_kind_is_dropped():
    binder = ProvenanceBinder(
        {
            "prov-invalid": {
                "prov_id": "prov-invalid",
                "kind": "made_up_source",
            }
        }
    )

    result = binder.bind_and_filter(
        [
            {
                "text": "Fact",
                "provenance": ["prov-invalid"],
            }
        ]
    )

    assert result == []
    assert binder.dropped_count == 1


def test_multiple_valid_provenance_refs_are_preserved():
    binder = ProvenanceBinder(
        {
            "prov-1": {
                "prov_id": "prov-1",
                "kind": "physician_entry",
            },
            "prov-2": {
                "prov_id": "prov-2",
                "kind": "image_bbox",
            },
        }
    )

    result = binder.bind_and_filter(
        [
            {
                "text": "Fact supported by two sources",
                "provenance": ["prov-1", "prov-2"],
            }
        ]
    )

    assert len(result) == 1
    assert result[0].provenance == (
        "prov-1",
        "prov-2",
    )


def test_duplicate_provenance_refs_are_deduplicated():
    binder = ProvenanceBinder(
        {
            "prov-1": {
                "prov_id": "prov-1",
                "kind": "physician_entry",
            }
        }
    )

    result = binder.bind_and_filter(
        [
            {
                "text": "Fact",
                "provenance": [
                    "prov-1",
                    "prov-1",
                    "prov-1",
                ],
            }
        ]
    )

    assert result[0].provenance == ("prov-1",)


def test_audio_without_retention_can_use_transcript():
    binder = ProvenanceBinder(
        {
            "prov-audio": {
                "prov_id": "prov-audio",
                "kind": "audio_offset",
                "retain_audio": False,
                "transcript": "Patient reports headache",
            }
        }
    )

    result = binder.bind_and_filter(
        [
            {
                "text": "Patient reports headache",
                "provenance": ["prov-audio"],
            }
        ]
    )

    assert len(result) == 1
    assert result[0].provenance == ("prov-audio",)


def test_audio_without_retention_and_without_transcript_is_dropped():
    binder = ProvenanceBinder(
        {
            "prov-audio": {
                "prov_id": "prov-audio",
                "kind": "audio_offset",
                "retain_audio": False,
            }
        }
    )

    result = binder.bind_and_filter(
        [
            {
                "text": "Patient reports headache",
                "provenance": ["prov-audio"],
            }
        ]
    )

    assert result == []
    assert binder.dropped_count == 1


def test_mixed_valid_and_invalid_refs_keep_valid_refs():
    binder = ProvenanceBinder(
        {
            "prov-valid": {
                "prov_id": "prov-valid",
                "kind": "physician_entry",
            }
        }
    )

    result = binder.bind_and_filter(
        [
            {
                "text": "Fact",
                "provenance": [
                    "prov-invalid",
                    "prov-valid",
                ],
            }
        ]
    )

    assert len(result) == 1
    assert result[0].provenance == ("prov-valid",)


def test_invalid_answered_by_degrades_to_unknown():
    binder = ProvenanceBinder(
        {
            "prov-1": {
                "prov_id": "prov-1",
                "kind": "text",
            }
        }
    )

    result = binder.bind_and_filter(
        [
            {
                "text": "Fact",
                "provenance": ["prov-1"],
                "answered_by": "invalid",
            }
        ]
    )

    assert result[0].answered_by == "unknown"


def test_empty_text_is_dropped():
    binder = ProvenanceBinder(
        {
            "prov-1": {
                "prov_id": "prov-1",
                "kind": "text",
            }
        }
    )

    result = binder.bind_and_filter(
        [
            {
                "text": "   ",
                "provenance": ["prov-1"],
            }
        ]
    )

    assert result == []
    assert binder.dropped_count == 1


def test_metrics_can_be_reset():
    binder = ProvenanceBinder({})

    binder.bind_and_filter(
        [
            {
                "text": "Fact",
                "provenance": [],
            }
        ]
    )

    assert binder.dropped_count == 1

    binder.reset_metrics()

    assert binder.dropped_count == 0
