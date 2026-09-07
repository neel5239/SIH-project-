from services.m3_conversation.services.dialogue_manager import (
    DialogueManager,
)


def test_chest_complaint_enters_cardiac_branch():
    manager = DialogueManager()

    result = manager.start_session(
        "chest-session",
    )

    assert result["question"]["id"] == "general.chief_complaint"

    result = manager.process_turn(
        "chest-session",
        text_english="I have chest pain.",
        asr_confidence=0.95,
    )

    # Chest pain first enters SOCRATES.
    assert result["next_question"]["id"] == "socrates.site"

    # Complete the SOCRATES branch.
    socrates_answers = [
        "The pain is in the center of my chest.",
        "It started suddenly today.",
        "It feels like pressure.",
        "It does not spread anywhere.",
        "I have no other symptoms.",
        "It happens from time to time.",
        "Walking makes it worse.",
        "It is severe.",
    ]

    for answer in socrates_answers:
        result = manager.process_turn(
            "chest-session",
            text_english=answer,
            asr_confidence=0.95,
        )

    assert (
        result["next_question"]["id"]
        == "systems.cardiac.chest_pressure"
    )


def test_chest_branch_continues_to_respiratory():
    manager = DialogueManager()

    manager.start_session(
        "chest-respiratory-session",
    )

    manager.process_turn(
        "chest-respiratory-session",
        text_english="I have chest pain.",
        asr_confidence=0.95,
    )

    socrates_answers = [
        "The pain is in my chest.",
        "It started today.",
        "It feels like pressure.",
        "It does not spread.",
        "No other symptoms.",
        "It happens sometimes.",
        "Activity makes it worse.",
        "It is severe.",
    ]

    for answer in socrates_answers:
        result = manager.process_turn(
            "chest-respiratory-session",
            text_english=answer,
            asr_confidence=0.95,
        )

    assert (
        result["next_question"]["id"]
        == "systems.cardiac.chest_pressure"
    )

    # Answer all cardiac questions.
    cardiac_answers = [
        "No.",
        "No.",
        "No.",
    ]

    for answer in cardiac_answers:
        result = manager.process_turn(
            "chest-respiratory-session",
            text_english=answer,
            asr_confidence=0.95,
        )

    assert (
        result["next_question"]["id"]
        == "systems.respiratory.cough"
    )


def test_abdominal_complaint_enters_gi_branch():
    manager = DialogueManager()

    manager.start_session(
        "abdomen-session",
    )

    result = manager.process_turn(
        "abdomen-session",
        text_english="I have abdominal pain.",
        asr_confidence=0.95,
    )

    assert result["next_question"]["id"] == "socrates.site"

    socrates_answers = [
        "The pain is in my abdomen.",
        "It started yesterday.",
        "It feels dull.",
        "It does not spread.",
        "I have nausea.",
        "It comes and goes.",
        "Food makes it worse.",
        "It is moderate.",
    ]

    for answer in socrates_answers:
        result = manager.process_turn(
            "abdomen-session",
            text_english=answer,
            asr_confidence=0.95,
        )

    assert (
        result["next_question"]["id"]
        == "systems.gi.nausea"
    )


def test_headache_enters_neurological_branch():
    manager = DialogueManager()

    manager.start_session(
        "neuro-session",
    )

    result = manager.process_turn(
        "neuro-session",
        text_english="I have a headache.",
        asr_confidence=0.95,
    )

    assert result["next_question"]["id"] == "socrates.site"

    socrates_answers = [
        "The pain is in my head.",
        "It started this morning.",
        "It is throbbing.",
        "It does not spread.",
        "I feel slightly dizzy.",
        "It comes and goes.",
        "Bright light makes it worse.",
        "It is moderate.",
    ]

    for answer in socrates_answers:
        result = manager.process_turn(
            "neuro-session",
            text_english=answer,
            asr_confidence=0.95,
        )

    assert (
        result["next_question"]["id"]
        == "systems.neuro.dizziness"
    )


def test_joint_complaint_enters_musculoskeletal_branch():
    manager = DialogueManager()

    manager.start_session(
        "msk-session",
    )

    result = manager.process_turn(
        "msk-session",
        text_english="I have knee joint pain.",
        asr_confidence=0.95,
    )

    assert result["next_question"]["id"] == "socrates.site"

    socrates_answers = [
        "The pain is in my knee.",
        "It started a week ago.",
        "It is aching.",
        "It does not spread.",
        "There are no other symptoms.",
        "It is worse after activity.",
        "Walking makes it worse.",
        "It is moderate.",
    ]

    for answer in socrates_answers:
        result = manager.process_turn(
            "msk-session",
            text_english=answer,
            asr_confidence=0.95,
        )

    assert (
        result["next_question"]["id"]
        == "systems.msk.swelling"
    )


def test_cough_enters_respiratory_branch():
    manager = DialogueManager()

    manager.start_session(
        "respiratory-session",
    )

    result = manager.process_turn(
        "respiratory-session",
        text_english="I have a cough.",
        asr_confidence=0.95,
    )

    assert (
        result["next_question"]["id"]
        == "systems.respiratory.cough"
    )