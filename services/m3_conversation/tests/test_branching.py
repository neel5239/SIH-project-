from services.m3_conversation.services.dialogue_manager import (
    DialogueManager,
)


def test_pain_complaint_enters_socrates_branch():
    manager = DialogueManager()

    result = manager.start_session(
        "pain-session",
    )

    assert result["question"]["id"] == "general.chief_complaint"

    result = manager.process_turn(
        "pain-session",
        text_english="I have severe chest pain.",
        asr_confidence=0.95,
    )

    assert result["state"] == "continue"
    assert result["next_question"]["id"] == "socrates.site"


def test_non_pain_complaint_does_not_enter_socrates():
    manager = DialogueManager()

    result = manager.start_session(
        "fever-session",
    )

    assert result["question"]["id"] == "general.chief_complaint"

    result = manager.process_turn(
        "fever-session",
        text_english="I have fever.",
        asr_confidence=0.95,
    )

    assert result["state"] == "continue"
    assert result["next_question"]["id"] == "hpi.duration"


def test_socrates_questions_progress():
    manager = DialogueManager()

    manager.start_session(
        "socrates-session",
    )

    result = manager.process_turn(
        "socrates-session",
        text_english="I have back pain.",
        asr_confidence=0.95,
    )

    assert result["next_question"]["id"] == "socrates.site"

    expected = [
        "socrates.onset",
        "socrates.character",
        "socrates.radiation",
        "socrates.associated_symptoms",
        "socrates.timing",
        "socrates.exacerbating",
        "socrates.severity",
    ]

    for expected_id in expected:
        result = manager.process_turn(
            "socrates-session",
            text_english="It is present in my back.",
            asr_confidence=0.95,
        )

        assert result["state"] == "continue"
        assert result["next_question"]["id"] == expected_id