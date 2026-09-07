from services.m5_fusion.models import (
    ClinicalSummary,
    DeltaSummary,
    PrakritiSummary,
    SummaryItem,
    TimelineItem,
)
from services.m5_fusion.services.physician_render import (
    PhysicianRenderer,
)


def make_summary():
    summary = ClinicalSummary(
        session_id="render-test",
        sections={
            "chief_complaint": [
                SummaryItem(
                    text="Headache for three days",
                    provenance=["prov-cc"],
                    answered_by="self",
                ),
            ],
            "hpi": [
                SummaryItem(
                    text="Pain is intermittent",
                    provenance=["prov-hpi"],
                    answered_by="proxy",
                ),
            ],
            "past_medical": [],
            "past_surgical": [],
            "drugs": [],
            "allergies": [],
            "family_history": [],
            "personal_history": [],
            "ros": [],
            "investigations": [],
        },
        alerts=["Conflict requires physician review: drug list"],
        timeline=[
            TimelineItem(
                date="2026-09-01",
                type="lab",
                text="CBC reviewed",
                provenance=["prov-lab"],
            )
        ],
        delta=DeltaSummary(
            is_return_visit=True,
            visit_number=2,
            changed=["Headache improved"],
            adherence_estimate=85.0,
        ),
    )

    summary.ayush.prakriti = PrakritiSummary(
        vata=0.44,
        pitta=0.36,
        kapha=0.20,
        dominant="vata-pitta",
        confidence=0.71,
        provisional=True,
        items_answered=12,
        items_total=30,
        provenance=["prov-prakriti"],
    )

    summary.ayush.codes = {
        "namaste": "AAE-16",
        "icd11_tm2": "SF7Y",
    }

    return summary


def test_renderer_preserves_section_order():
    renderer = PhysicianRenderer()

    rendered = renderer.render(make_summary())

    assert list(rendered.sections.keys()) == [
        "Chief Complaint",
        "HPI",
        "Past Medical History",
        "Past Surgical History",
        "Drugs",
        "Allergies",
        "Family History",
        "Personal History",
        "Review of Systems",
        "Investigations",
    ]


def test_alerts_are_rendered_separately():
    renderer = PhysicianRenderer()

    rendered = renderer.render(make_summary())

    assert rendered.alerts == [
        "Conflict requires physician review: drug list"
    ]


def test_provenance_is_visible():
    renderer = PhysicianRenderer()

    rendered = renderer.render(make_summary())

    item = rendered.sections["Chief Complaint"][0]

    assert "prov-cc" in item
    assert "source:" in item


def test_proxy_marker_is_visible():
    renderer = PhysicianRenderer()

    rendered = renderer.render(make_summary())

    item = rendered.sections["HPI"][0]

    assert "[PROXY]" in item


def test_timeline_preserves_provenance():
    renderer = PhysicianRenderer()

    rendered = renderer.render(make_summary())

    assert rendered.timeline == [
        "2026-09-01 | lab | CBC reviewed [source: prov-lab]"
    ]


def test_return_visit_delta_is_rendered():
    renderer = PhysicianRenderer()

    rendered = renderer.render(make_summary())

    assert "Visit number: 2" in rendered.delta
    assert "Headache improved" in rendered.delta
    assert any(
        "85%" in item
        for item in rendered.delta
    )


def test_adherence_is_marked_as_estimate():
    renderer = PhysicianRenderer()

    rendered = renderer.render(make_summary())

    assert any(
        "estimate, not a confirmed fact" in item
        for item in rendered.delta
    )


def test_ayush_is_rendered():
    renderer = PhysicianRenderer()

    rendered = renderer.render(make_summary())

    assert "prakriti" in rendered.ayush
    assert rendered.ayush["prakriti"]["dominant"] == "vata-pitta"
    assert rendered.ayush["codes"]["namaste"] == "AAE-16"
    assert rendered.ayush["codes"]["icd11_tm2"] == "SF7Y"


def test_ayush_can_be_hidden_for_non_ayush_opd():
    renderer = PhysicianRenderer()

    rendered = renderer.render(
        make_summary(),
        ayush_opd=False,
    )

    assert rendered.ayush == {}


def test_plain_text_places_alerts_first():
    renderer = PhysicianRenderer()

    text = renderer.render_text(make_summary())

    assert text.startswith("ALERTS")
    assert text.index("ALERTS") < text.index(
        "CHIEF COMPLAINT"
    )


def test_plain_text_contains_proxy_marker():
    renderer = PhysicianRenderer()

    text = renderer.render_text(make_summary())

    assert "[PROXY]" in text


def test_plain_text_contains_provenance():
    renderer = PhysicianRenderer()

    text = renderer.render_text(make_summary())

    assert "[source: prov-cc]" in text
    assert "[source: prov-hpi]" in text


def test_renderer_does_not_invent_missing_sections():
    renderer = PhysicianRenderer()

    summary = ClinicalSummary(
        session_id="empty",
    )

    rendered = renderer.render(summary)

    assert all(
        value == []
        for value in rendered.sections.values()
    )
    assert rendered.alerts == []
    assert rendered.timeline == []
    assert rendered.delta == []


def test_renderer_marks_missing_item_provenance():
    renderer = PhysicianRenderer()

    summary = ClinicalSummary(
        session_id="unsafe-render",
        sections={
            "chief_complaint": [
                SummaryItem(
                    text="Unsafely constructed fact",
                    provenance=[],
                )
            ],
            "hpi": [],
            "past_medical": [],
            "past_surgical": [],
            "drugs": [],
            "allergies": [],
            "family_history": [],
            "personal_history": [],
            "ros": [],
            "investigations": [],
        },
    )

    rendered = renderer.render(summary)

    assert rendered.sections["Chief Complaint"] == [
        "[UNRENDERED: missing provenance]"
    ]


def test_render_is_deterministic():
    renderer = PhysicianRenderer()

    summary = make_summary()

    first = renderer.render_text(summary)
    second = renderer.render_text(summary)

    assert first == second
