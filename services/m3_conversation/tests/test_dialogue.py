from services.m3_conversation.services.dialogue_manager import (
    DialogueManager,
)


def test_ten_question_linear_interview():
    manager = DialogueManager()

    result = manager.start_session(
        "test-session-001",
    )

    assert result["state"] == "continue"
    assert result["question"]["id"] == "general.chief_complaint"
    assert result["progress"]["questions_asked"] == 0

    answers = [
        "I have fever.",
        "For three days.",
        "It is moderate.",
        "It started three days ago.",
        "I feel it mainly in my chest.",
        "It feels like a dull discomfort.",
        "It becomes worse when I exert myself.",
        "Rest makes it better.",
        "I also have body ache.",
        "I have no major medical conditions.",
    ]

    expected_next = [
        "hpi.duration",
        "hpi.severity",
        "hpi.onset",
        "hpi.location",
        "hpi.character",
        "hpi.aggravating_factors",
        "hpi.relieving_factors",
        "hpi.associated_symptoms",
        "general.past_medical_history",
        None,
    ]

    for answer, expected in zip(
        answers,
        expected_next,
    ):
        result = manager.process_turn(
            "test-session-001",
            text_english=answer,
            audio_provenance_ref="audio-001",
            asr_confidence=0.94,
        )

        if expected is None:
            assert result["state"] == "continue"
            assert result["next_question"] is not None
            assert result["next_question"]["id"].startswith(
                "ros."
            )
        else:
            assert result["state"] == "continue"
            assert result["next_question"]["id"] == expected


def test_touch_input():
    manager = DialogueManager()

    manager.start_session(
        "touch-session",
    )

    # First answer the chief complaint.
    manager.process_turn(
        "touch-session",
        text_english="I have fever.",
        input_mode="voice",
    )

    # Now duration is the active question.
    result = manager.process_turn(
        "touch-session",
        touch_selection="two_to_three_days",
        input_mode="touch",
    )

    assert len(result["slots_filled"]) == 1

    slot = result["slots_filled"][0]

    assert slot["ontology_key"] == "hpi.duration"
    assert slot["value"] == "two_to_three_days"
    assert slot["input_mode"] == "touch"


def test_provenance_and_proxy_are_preserved():
    manager = DialogueManager()

    manager.start_session(
        "proxy-session",
    )

    result = manager.process_turn(
        "proxy-session",
        text_english="They have fever.",
        audio_provenance_ref="blob-123:0-48000",
        asr_confidence=0.91,
        answered_by="proxy",
        input_mode="voice",
    )

    slot = result["slots_filled"][0]

    assert slot["provenance_id"] == "blob-123:0-48000"
    assert slot["answered_by"] == "proxy"
    assert slot["input_mode"] == "voice"