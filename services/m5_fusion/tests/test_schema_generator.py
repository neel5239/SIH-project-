import pytest

from services.m5_fusion.services.schema_generator import (
    ALLOWED_SECTIONS,
    SchemaConstrainedGenerator,
    SchemaGenerationError,
)


def test_generator_renders_sourced_item():
    generator = SchemaConstrainedGenerator()

    result = generator.generate(
        sections={
            "chief_complaint": [
                {
                    "text": "Headache for three days",
                    "provenance": ["prov-1"],
                    "answered_by": "self",
                }
            ]
        }
    )

    assert result["chief_complaint"] == [
        {
            "text": "Headache for three days",
            "provenance": ["prov-1"],
            "answered_by": "self",
        }
    ]


def test_generator_initializes_all_allowed_sections():
    generator = SchemaConstrainedGenerator()

    result = generator.generate(sections={})

    assert tuple(result.keys()) == ALLOWED_SECTIONS

    for section in ALLOWED_SECTIONS:
        assert result[section] == []


def test_missing_provenance_is_rejected():
    generator = SchemaConstrainedGenerator()

    with pytest.raises(SchemaGenerationError):
        generator.generate(
            sections={
                "hpi": [
                    {
                        "text": "Patient reports pain",
                        "provenance": [],
                    }
                ]
            }
        )


def test_missing_provenance_field_is_rejected():
    generator = SchemaConstrainedGenerator()

    with pytest.raises(SchemaGenerationError):
        generator.generate(
            sections={
                "hpi": [
                    {
                        "text": "Patient reports pain",
                    }
                ]
            }
        )


def test_empty_text_is_rejected():
    generator = SchemaConstrainedGenerator()

    with pytest.raises(SchemaGenerationError):
        generator.generate(
            sections={
                "hpi": [
                    {
                        "text": "   ",
                        "provenance": ["prov-1"],
                    }
                ]
            }
        )


def test_unknown_section_is_rejected():
    generator = SchemaConstrainedGenerator()

    with pytest.raises(SchemaGenerationError):
        generator.generate(
            sections={
                "unsupported_section": [
                    {
                        "text": "Some fact",
                        "provenance": ["prov-1"],
                    }
                ]
            }
        )


def test_invalid_answered_by_degrades_to_unknown():
    generator = SchemaConstrainedGenerator()

    result = generator.generate(
        sections={
            "hpi": [
                {
                    "text": "Patient reports pain",
                    "provenance": ["prov-1"],
                    "answered_by": "invalid-value",
                }
            ]
        }
    )

    assert result["hpi"][0]["answered_by"] == "unknown"


def test_provenance_values_are_normalized():
    generator = SchemaConstrainedGenerator()

    result = generator.generate(
        sections={
            "hpi": [
                {
                    "text": "Pain reported",
                    "provenance": [
                        " prov-1 ",
                        "",
                        "prov-2",
                    ],
                }
            ]
        }
    )

    assert result["hpi"][0]["provenance"] == [
        "prov-1",
        "prov-2",
    ]


def test_template_fallback_does_not_invent_content():
    item = SchemaConstrainedGenerator.template_from_summary_item(
        text="Headache for three days",
        provenance=["prov-1"],
        answered_by="self",
    )

    assert item.to_dict() == {
        "text": "Headache for three days",
        "provenance": ["prov-1"],
        "answered_by": "self",
    }
