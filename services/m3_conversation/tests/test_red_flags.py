from services.m3_conversation.services.red_flag_engine import RedFlagEngine


EXPECTED_RULE_IDS = {
    "CARDIAC-01",
    "STROKE-01",
    "RESP-01",
    "BLEED-01",
    "SEPSIS-01",
    "ABDO-01",
    "NEURO-01",
    "PEDS-01",
    "OBS-01",
    "TRAUMA-01",
    "SUICIDE-01",
    "ANAPH-01",
}


def test_red_flag_ontology_contains_required_rules():
    engine = RedFlagEngine()

    assert engine.rule_count() == 12
    assert set(engine.rule_ids()) == EXPECTED_RULE_IDS


def test_cardiac_rule_fires():
    engine = RedFlagEngine()

    events = engine.evaluate(
        slots={
            "socrates.site": "chest",
            "socrates.radiation": ["left_arm"],
            "socrates.onset": 6,
        }
    )

    assert len(events) == 1
    assert events[0].rule_id == "CARDIAC-01"
    assert events[0].severity == "critical"
    assert events[0].action == "abort_and_escalate"
    assert events[0].detector == "rule"


def test_cardiac_rule_does_not_fire_without_danger_signal():
    engine = RedFlagEngine()

    events = engine.evaluate(
        slots={
            "socrates.site": "chest",
            "socrates.radiation": ["none"],
            "socrates.onset": 6,
        }
    )

    assert events == []


def test_stroke_rule_fires():
    engine = RedFlagEngine()

    events = engine.evaluate(
        slots={
            "general.chief_complaint": "sudden face droop, arm weakness and speech difficulty",
            "socrates.onset": "suddenly",
        }
    )

    assert any(event.rule_id == "STROKE-01" for event in events)


def test_respiratory_rule_fires():
    engine = RedFlagEngine()

    events = engine.evaluate(
        slots={
            "general.chief_complaint": "severe breathlessness at rest",
        }
    )

    assert any(event.rule_id == "RESP-01" for event in events)


def test_bleeding_rule_fires():
    engine = RedFlagEngine()

    events = engine.evaluate(
        slots={
            "general.chief_complaint": "vomiting blood",
        }
    )

    assert any(event.rule_id == "BLEED-01" for event in events)


def test_self_harm_rule_fires():
    engine = RedFlagEngine()

    events = engine.evaluate(
        slots={
            "general.chief_complaint": "I want to kill myself",
        }
    )

    assert any(event.rule_id == "SUICIDE-01" for event in events)


def test_anaphylaxis_rule_fires():
    engine = RedFlagEngine()

    events = engine.evaluate(
        slots={
            "general.chief_complaint": "my face and tongue are swollen",
            "hpi.associated_symptoms": "breathing difficulty",
        }
    )

    assert any(event.rule_id == "ANAPH-01" for event in events)


def test_rule_event_is_preserved_when_ml_adds_another_flag():
    engine = RedFlagEngine()

    ml_event = engine.evaluate(
        slots={
            "general.chief_complaint": "unrelated complaint",
        }
    )

    fake_ml_event = engine.evaluate(
        slots={
            "general.chief_complaint": "I want to kill myself",
        }
    )[0]

    events = engine.evaluate_with_ml(
        slots={
            "socrates.site": "chest",
            "socrates.radiation": ["left_arm"],
            "socrates.onset": 6,
        },
        ml_events=[
            fake_ml_event,
        ],
    )

    rule_ids = {event.rule_id for event in events}

    assert "CARDIAC-01" in rule_ids
    assert "SUICIDE-01" in rule_ids


def test_rule_based_detection_is_not_suppressible_by_empty_ml_result():
    engine = RedFlagEngine()

    events = engine.evaluate_with_ml(
        slots={
            "socrates.site": "chest",
            "socrates.radiation": ["left_arm"],
            "socrates.onset": 6,
        },
        ml_events=[],
    )

    assert any(event.rule_id == "CARDIAC-01" for event in events)
