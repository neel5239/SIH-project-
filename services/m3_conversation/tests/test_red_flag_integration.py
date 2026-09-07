from services.m3_conversation.services.dialogue_manager import DialogueManager


def _answer_current_question(manager, session_id, text):
    return manager.process_turn(
        session_id,
        text_english=text,
        input_mode="voice",
        answered_by="self",
    )


def test_cardiac_red_flag_aborts_interview_and_preserves_slots():
    manager = DialogueManager()
    session_id = "red-flag-cardiac-integration"

    start = manager.start_session(session_id)

    assert start["state"] == "continue"
    assert start["question"] is not None

    # First turn: establish the chief complaint.
    result = _answer_current_question(
        manager,
        session_id,
        "I have chest pain",
    )

    assert result["state"] == "continue"
    assert result["next_question"] is not None

    # Complete the SOCRATES information required by CARDIAC-01.
    # The exact questions are selected adaptively by M3.
    safety_limit = 20

    for _ in range(safety_limit):
        question = result["next_question"]

        if question is None:
            break

        question_id = question["id"]

        if question_id == "socrates.site":
            answer = "chest"

        elif question_id == "socrates.onset":
            answer = "suddenly, 2 hours ago"

        elif question_id == "socrates.radiation":
            answer = "pain radiates to my left arm"

        elif question_id == "socrates.associated_symptoms":
            answer = "sweating"

        else:
            answer = "No"

        result = _answer_current_question(
            manager,
            session_id,
            answer,
        )

        if result["state"] == "aborted":
            break

    assert result["state"] == "aborted"
    assert result["end_reason"] == "red_flag"
    assert result["next_question"] is None

    assert result["red_flag"] is not None
    assert result["red_flag"]["rule_id"] == "CARDIAC-01"

    assert result["escalation"]["action"] == "abort_and_escalate"
    assert result["escalation"]["message_en"] == (
        "Please stay here. A nurse is coming now."
    )
    assert result["escalation"]["notify"] == [
        "triage_desk",
        "physician_on_duty",
    ]

    state = manager.get_state(session_id)

    assert state.active is False
    assert state.end_reason == "red_flag"

    slots = manager.get_slots(session_id)
    slot_keys = {slot["ontology_key"] for slot in slots}

    assert "general.chief_complaint" in slot_keys


def test_no_red_flag_allows_interview_to_continue():
    manager = DialogueManager()
    session_id = "red-flag-negative-integration"

    start = manager.start_session(session_id)

    assert start["state"] == "continue"

    result = _answer_current_question(
        manager,
        session_id,
        "I have mild stomach discomfort",
    )

    assert result["state"] == "continue"
    assert result["red_flag"] is None
    assert result["next_question"] is not None

    state = manager.get_state(session_id)

    assert state.active is True
    assert state.end_reason is None


def test_red_flag_abort_preserves_partial_slot_data():
    manager = DialogueManager()
    session_id = "red-flag-partial-slots"

    manager.start_session(session_id)

    result = _answer_current_question(
        manager,
        session_id,
        "I have chest pain",
    )

    assert result["state"] == "continue"

    # Force a cardiac danger pattern using the questions
    # that M3 has already selected.
    for _ in range(20):
        question = result["next_question"]

        if question is None:
            break

        question_id = question["id"]

        answers = {
            "socrates.site": "chest",
            "socrates.onset": "suddenly, 1 hour ago",
            "socrates.radiation": "left arm",
            "socrates.associated_symptoms": "sweating",
        }

        answer = answers.get(question_id, "No")

        result = _answer_current_question(
            manager,
            session_id,
            answer,
        )

        if result["state"] == "aborted":
            break

    assert result["state"] == "aborted"

    slots = manager.get_slots(session_id)

    assert len(slots) >= 1

    chief_complaint = next(
        slot
        for slot in slots
        if slot["ontology_key"] == "general.chief_complaint"
    )

    assert chief_complaint["value"] == "I have chest pain"
